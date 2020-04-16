from datetime import datetime
from math import floor

from discord import Message
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from config import CONFIG
from karma.parser import parse_message, create_transactions
from models import User, Karma, KarmaChange
from utils.aliases import get_name_string


def process_karma(message: Message, message_id: int, db_session: Session, timeout: int):
    reply = ""

    # Parse the message for karma modifications
    raw_karma = parse_message(message.clean_content, db_session)

    # If no karma'd items, just return
    if not raw_karma:
        return reply

    # TODO: Protect from byte-limit length chars

    # If the author was IRC, set the display name to be the irc user that karma'd, else use original display name
    display_name = message.author.display_name
    if message.author.id == CONFIG["UWCS_DISCORD_BRIDGE_BOT_ID"]:
        # Gets the username of the irc user
        display_name = message.content.split(" ")[0][3:-3]

    # Process the raw karma tokens into a number of karma transactions
    transactions = create_transactions(message.author.name, display_name, raw_karma)

    if not transactions:
        return reply

    # Get karma-ing user
    user = db_session.query(User).filter(User.user_uid == message.author.id).first()

    # Start preparing the reply string
    if len(transactions) > 1:
        transaction_plural = "s"
    else:
        transaction_plural = ""

    item_str = ""
    error_str = ""

    # Iterate over the transactions to write them to the database
    for transaction in transactions:
        # Truncate the name safely so we 2000 char karmas can be used
        truncated_name = (
            (transaction.name[300:] + ".. (truncated to 300 chars)")
            if len(transaction.name) > 300
            else transaction.name
        )

        # Catch any self-karma transactions early
        if transaction.self_karma and transaction.net_karma > -1:
            error_str += f' • Could not change "{truncated_name}" because you cannot change your own karma! :angry:\n'
            continue

        # Get the karma item from the database if it exists
        karma_item = (
            db_session.query(Karma)
            .filter(func.lower(Karma.name) == func.lower(transaction.name))
            .one_or_none()
        )

        # Update or create the karma item
        if not karma_item:
            karma_item = Karma(name=transaction.name)
            db_session.add(karma_item)
            db_session.commit()

        # Get the last change (or none if there was none)
        last_change = (
            db_session.query(KarmaChange)
            .filter(KarmaChange.karma_id == karma_item.id)
            .order_by(desc(KarmaChange.created_at))
            .first()
        )

        if not last_change:
            # If the bot is being downvoted then the karma can only go up
            if transaction.name.lower() == "apollo":
                new_score = abs(transaction.net_karma)
            else:
                new_score = transaction.net_karma

            karma_change = KarmaChange(
                karma_id=karma_item.id,
                user_id=user.id,
                message_id=message_id,
                reasons=transaction.reasons,
                change=new_score,
                score=new_score,
                created_at=datetime.utcnow(),
            )
            db_session.add(karma_change)
            db_session.commit()
        else:
            time_delta = datetime.utcnow() - last_change.created_at

            if time_delta.seconds >= timeout:
                # If the bot is being downvoted then the karma can only go up
                if transaction.name.lower() == "apollo":
                    new_score = last_change.score + abs(transaction.net_karma)
                else:
                    new_score = last_change.score + transaction.net_karma

                karma_change = KarmaChange(
                    karma_id=karma_item.id,
                    user_id=user.id,
                    message_id=message_id,
                    reasons=transaction.reasons,
                    score=new_score,
                    change=(new_score - last_change.score),
                    created_at=datetime.utcnow(),
                )
                db_session.add(karma_change)
                db_session.commit()
            else:
                # Tell the user that the item is on cooldown
                if time_delta.seconds < 60:
                    error_str += f' • Could not change "{truncated_name}" since it is still on cooldown (last altered {time_delta.seconds} seconds ago).\n'
                else:
                    mins_plural = ""
                    mins = floor(time_delta.seconds / 60)
                    if time_delta.seconds >= 120:
                        mins_plural = "s"
                    error_str += f' • Could not change "{truncated_name}" since it is still on cooldown (last altered {mins} minute{mins_plural} ago).\n'

                continue

        # Update karma counts
        if transaction.net_karma == 0:
            karma_item.neutrals = karma_item.neutrals + 1
        elif transaction.net_karma == 1:
            karma_item.pluses = karma_item.pluses + 1
        elif transaction.net_karma == -1:
            # Make sure the changed operation is updated
            if transaction.name.lower() == "apollo":
                karma_item.pluses = karma_item.pluses + 1
            else:
                karma_item.minuses = karma_item.minuses + 1

        # Give some sass if someone is trying to downvote the bot
        if (
            transaction.name.casefold() == "Apollo".casefold()
            and transaction.net_karma < 0
        ):
            apollo_response = ":wink:"
        else:
            apollo_response = ""

        # Build the karma item string
        if transaction.reasons:
            if len(transaction.reasons) > 1:
                reasons_plural = "s"
                reasons_has = "have"
            else:
                reasons_plural = ""
                reasons_has = "has"

            if transaction.self_karma:
                item_str += f" • **{truncated_name}** (new score is {karma_change.score}) and your reason{reasons_plural} {reasons_has} been recorded. *Fool!* that's less karma to you. :smiling_imp:\n"
            else:
                item_str += f" • **{truncated_name}** (new score is {karma_change.score}) and your reason{reasons_plural} {reasons_has} been recorded. {apollo_response}\n"
        else:
            if transaction.self_karma:
                item_str += f" • **{truncated_name}** (new score is {karma_change.score}). *Fool!* that's less karma to you. :smiling_imp:\n"
            else:
                item_str += f" • **{truncated_name}** (new score is {karma_change.score}). {apollo_response}\n"

    # Get the name, either from discord or irc
    author_display = get_name_string(message)

    # Construct the reply string in totality
    # If you have error(s) and no items processed successfully
    if not item_str and error_str:
        reply = f"Sorry {author_display}, I couldn't karma the requested item{transaction_plural} because of the following problem{transaction_plural}:\n\n{error_str}"
    # If you have items processed successfully but some errors too
    elif item_str and error_str:
        reply = f"Thanks {author_display}, I have made changes to the following item(s) karma:\n\n{item_str}\n\nThere were some issues with the following item(s), too:\n\n{error_str}"
    # If all items were processed successfully
    else:
        reply = f"Thanks {author_display}, I have made changes to the following karma item{transaction_plural}:\n\n{item_str}"

    # Commit any changes (in case of any DB inconsistencies)
    db_session.commit()
    return reply.rstrip()
