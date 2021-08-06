import logging
import unicodedata
from datetime import datetime, timedelta

from discord import Message
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy_utils import ScalarListException

from cogs.commands.admin import MiniKarmaMode
from config import CONFIG
from karma.parser import parse_message_content
from karma.transaction import (
    KarmaTransaction,
    apply_blacklist,
    filter_transactions,
    make_transactions,
)
from models import Karma, KarmaChange, MiniKarmaChannel
from utils import filter_out_none, get_database_user, get_name_string


def is_in_cooldown(last_change, timeout):
    timeout_time = datetime.utcnow() - timedelta(seconds=timeout)
    return last_change.created_at > timeout_time


def process_karma(message: Message, message_id: int, db_session: Session, timeout: int):
    reply = ""

    # Parse the message for karma modifications
    karma_items = parse_message_content(message.content)
    transactions = make_transactions(karma_items, message)
    transactions = filter_transactions(transactions)
    transactions = apply_blacklist(transactions, db_session)

    # If no karma'd items, just return
    if not transactions:
        return reply

    # TODO: Protect from byte-limit length chars

    # Get karma-ing user
    user = get_database_user(message.author)

    # Get whether the channel is on mini karma or not
    channel = (
        db_session.query(MiniKarmaChannel)
        .filter(MiniKarmaChannel.channel == message.channel.id)
        .one_or_none()
    )
    if channel is None:
        karma_mode = MiniKarmaMode.Normal
    else:
        karma_mode = MiniKarmaMode.Mini

    def own_karma_error(topic):
        if karma_mode == MiniKarmaMode.Normal:
            return f' • Could not change "{topic}" because you cannot change your own karma! :angry:'
        else:
            return f'could not change "**{topic}**" (own name)'

    def internal_error(topic):
        if karma_mode == MiniKarmaMode.Normal:
            return f' • Could not create "{topic}" due to an internal error.'
        else:
            return f'could not change "**{topic}**" (internal error)'

    def cooldown_error(topic, td):
        # Tell the user that the item is on cooldown
        if td.seconds < 60:
            seconds_plural = f"second{'s' if td.seconds != 1 else ''}"
            duration = f"{td.seconds} {seconds_plural}"
        else:
            mins = td.seconds // 60
            mins_plural = f"minute{'s' if mins != 1 else ''}"
            duration = f"{mins} {mins_plural}"

        if karma_mode == MiniKarmaMode.Normal:
            return f' • Could not change "{topic}" since it is still on cooldown (last altered {duration} ago).\n'
        else:
            return (
                f'could not change "**{topic}**" (cooldown, last edit {duration} ago)'
            )

    def success_item(tr: KarmaTransaction):
        # Give some sass if someone is trying to downvote the bot
        if (
            tr.karma_item.topic.casefold() == "apollo"
            and tr.karma_item.operation.value < 0
        ):
            apollo_response = ":wink:"
        else:
            apollo_response = ""

        op = str(tr.karma_item.operation)

        # Build the karma item string
        if tr.karma_item.reason:
            if karma_mode == MiniKarmaMode.Normal:
                if tr.self_karma:
                    return f" • **{truncated_name}** (new score is {karma_change.score}) and your reason has been recorded. *Fool!* that's less karma to you. :smiling_imp:"
                else:
                    return f" • **{truncated_name}** (new score is {karma_change.score}) and your reason has been recorded. {apollo_response}"
            else:
                return f"**{truncated_name}**{op} (now {karma_change.score}, reason recorded)"

        else:
            if karma_mode == MiniKarmaMode.Normal:
                if tr.self_karma:
                    return f" • **{truncated_name}** (new score is {karma_change.score}). *Fool!* that's less karma to you. :smiling_imp:"
                else:
                    return f" • **{truncated_name}** (new score is {karma_change.score}). {apollo_response}"
            else:
                return f"**{truncated_name}**{op} (now {karma_change.score})"

    # Start preparing the reply string
    if len(transactions) > 1:
        transaction_plural = "s"
    else:
        transaction_plural = ""

    items = []
    errors = []

    # Iterate over the transactions to write them to the database
    for transaction in transactions:
        # Truncate the topic safely so we 2000 char karmas can be used
        truncated_name = (
            (transaction.karma_item.topic[300:] + ".. (truncated to 300 chars)")
            if len(transaction.karma_item.topic) > 300
            else transaction.karma_item.topic
        )

        # Catch any self-karma transactions early
        if transaction.self_karma and transaction.karma_item.operation.value > -1:
            errors.append(own_karma_error(truncated_name))
            continue

        def topic_transformations():
            def query(t):
                return db_session.query(Karma).filter(Karma.name.ilike(t)).one_or_none()

            topic = transaction.karma_item.topic.casefold()
            yield query(topic)
            yield query(topic.replace(" ", "_"))
            yield query(topic.replace("_", " "))
            topic = unicodedata.normalize(CONFIG.UNICODE_NORMALISATION_FORM, topic)
            yield query(topic)
            yield query(topic.replace(" ", "_"))
            yield query(topic.replace("_", " "))
            topic = "".join(c for c in topic if not unicodedata.combining(c))
            yield query(topic)
            yield query(topic.replace(" ", "_"))
            yield query(topic.replace("_", " "))

        # Get the karma item from the database if it exists
        karma_item = next(filter_out_none(topic_transformations()), None)

        # Update or create the karma item
        if not karma_item:
            karma_item = Karma(name=transaction.karma_item.topic)
            db_session.add(karma_item)
            try:
                db_session.commit()
            except (ScalarListException, SQLAlchemyError) as e:
                db_session.rollback()
                logging.exception(e)
                errors.append(internal_error(truncated_name))
                continue

        # Get the last change (or none if there was none)
        last_change = (
            db_session.query(KarmaChange)
            .filter(KarmaChange.karma_id == karma_item.id)
            .order_by(desc(KarmaChange.created_at))
            .first()
        )

        if not last_change:
            # If the bot is being downvoted then the karma can only go up
            if transaction.karma_item.topic.casefold() == "apollo":
                new_score = abs(transaction.karma_item.operation.value)
            else:
                new_score = transaction.karma_item.operation.value

            karma_change = KarmaChange(
                karma_id=karma_item.id,
                user_id=user.id,
                message_id=message_id,
                reason=transaction.karma_item.reason,
                change=new_score,
                score=new_score,
                created_at=datetime.utcnow(),
            )
            db_session.add(karma_change)
            try:
                db_session.commit()
            except (ScalarListException, SQLAlchemyError) as e:
                db_session.rollback()
                logging.exception(e)
                errors.append(internal_error(truncated_name))
                continue
        else:
            time_delta = datetime.utcnow() - last_change.created_at
            if is_in_cooldown(last_change, timeout):
                errors.append(cooldown_error(truncated_name, time_delta))
                continue

            # If the bot is being downvoted then the karma can only go up
            if transaction.karma_item.topic.casefold() == "apollo":
                new_score = last_change.score + abs(
                    transaction.karma_item.operation.value
                )
            else:
                new_score = last_change.score + transaction.karma_item.operation.value

            karma_change = KarmaChange(
                karma_id=karma_item.id,
                user_id=user.id,
                message_id=message_id,
                reason=transaction.karma_item.reason,
                score=new_score,
                change=(new_score - last_change.score),
                created_at=datetime.utcnow(),
            )
            db_session.add(karma_change)
            try:
                db_session.commit()
            except (ScalarListException, SQLAlchemyError) as e:
                db_session.rollback()
                logging.exception(e)
                errors.append(internal_error(truncated_name))
                karma_change = KarmaChange(
                    karma_id=karma_item.id,
                    user_id=user.id,
                    message_id=message_id,
                    reason=transaction.karma_item.reason,
                    score=new_score,
                    change=(new_score - last_change.score),
                    created_at=datetime.utcnow(),
                )
                db_session.add(karma_change)
                try:
                    db_session.commit()
                except (ScalarListException, SQLAlchemyError) as e:
                    db_session.rollback()
                    logging.exception(e)
                    errors.append(internal_error(truncated_name))
                    continue

        # Update karma counts
        if transaction.karma_item.operation.value == 0:
            karma_item.neutrals = karma_item.neutrals + 1
        elif transaction.karma_item.operation.value == 1:
            karma_item.pluses = karma_item.pluses + 1
        elif transaction.karma_item.operation.value == -1:
            # Make sure the changed operation is updated
            if transaction.karma_item.topic.casefold() == "apollo":
                karma_item.pluses = karma_item.pluses + 1
            else:
                karma_item.minuses = karma_item.minuses + 1

        items.append(success_item(transaction))

    # Get the name, either from discord or irc
    author_display = get_name_string(message)

    # Construct the reply string in totality
    # If you have error(s) and no items processed successfully
    if karma_mode == MiniKarmaMode.Normal:
        item_str = "\n".join(items)
        error_str = "\n".join(errors)
        if not item_str and error_str:
            reply = f"Sorry {author_display}, I couldn't karma the requested item{transaction_plural} because of the following problem{transaction_plural}:\n\n{error_str}"
        # If you have items processed successfully but some errors too
        elif item_str and error_str:
            reply = f"Thanks {author_display}, I have made changes to the following item(s) karma:\n\n{item_str}\n\nThere were some issues with the following item(s), too:\n\n{error_str}"
        # If all items were processed successfully
        else:
            reply = f"Thanks {author_display}, I have made changes to the following karma item{transaction_plural}:\n\n{item_str}"
    else:
        item_str = " ".join(items)
        error_str = " ".join(errors)
        reply = " ".join(filter(None, ["Changes:", item_str, error_str]))

    # Commit any changes (in case of any DB inconsistencies)
    try:
        db_session.commit()
    except (ScalarListException, SQLAlchemyError) as e:
        logging.exception(e)
        db_session.rollback()
    return reply.rstrip()
