from datetime import datetime
from math import floor

from sqlalchemy import func, desc

from karma.parser import parse_message, create_transactions
from models import User, Karma, KarmaChange


def process_karma(message, message_id, db_session, timeout):
    reply = ''

    # Parse the message for karma modifications
    raw_karma = parse_message(message.clean_content)

    # If no karma'd items, just return
    if not raw_karma:
        return reply

    # Process the raw karma tokens into a number of karma transactions
    transactions = create_transactions(message.author.name, message.author.display_name, raw_karma)

    if not transactions:
        return reply

    # Get karma-ing user
    user = db_session.query(User).filter(User.user_uid == message.author.id).first()

    # Start preparing the reply string
    if len(transactions) > 1:
        transaction_plural = 's'
    else:
        transaction_plural = ''

    item_str = ''
    error_str = ''

    # Iterate over the transactions to write them to the database
    for transaction in transactions:
        # Catch any self-karma transactions early
        if transaction.self_karma:
            error_str += f' - Could not change **{transaction.name}** because you cannot change your own karma, you *fool!*\n'
            continue

        # Get the karma item from the database if it exists
        karma_item = db_session.query(Karma).filter(
            func.lower(Karma.name) == func.lower(transaction.name)).one_or_none()

        # Update or create the karma item
        if not karma_item:
            karma_item = Karma(name=func.lower(transaction.name))
            db_session.add(karma_item)
            db_session.commit()

        # Get the last change (or none if there was none)
        last_change = db_session.query(KarmaChange).filter(KarmaChange.karma_id == karma_item.id).order_by(
            desc(KarmaChange.created_at)).first()

        if not last_change:
            karma_change = KarmaChange(karma_id=karma_item.id, user_id=user.id, message_id=message_id,
                                       reasons=transaction.reasons, change=transaction.net_karma,
                                       score=transaction.net_karma, created_at=datetime.utcnow())
            db_session.add(karma_change)
            db_session.commit()
        else:
            time_delta = datetime.utcnow() - last_change.created_at

            if time_delta.seconds >= timeout:
                karma_change = KarmaChange(karma_id=karma_item.id, user_id=user.id, message_id=message_id,
                                           reasons=transaction.reasons, change=transaction.net_karma,
                                           score=(last_change.score + transaction.net_karma),
                                           created_at=datetime.utcnow())
                db_session.add(karma_change)
                db_session.commit()
            else:
                if time_delta.seconds < 60:
                    error_str += f' • Could not change **{karma_item.name}** since it is still on cooldown (last altered {time_delta.seconds} seconds ago).\n'
                else:
                    mins_plural = ''
                    mins = floor(time_delta.seconds / 60)
                    if time_delta.seconds >= 120:
                        mins_plural = 's'
                    error_str += f' • Could not change **{karma_item.name}** since it is still on cooldown (last altered {mins} minute{mins_plural} ago).\n'

                continue

        if transaction.net_karma == 0:
            karma_item.neutrals = karma_item.neutrals + 1
        elif transaction.net_karma == 1:
            karma_item.pluses = karma_item.pluses + 1
        elif transaction.net_karma == -1:
            karma_item.minuses = karma_item.minuses + 1

        # Build the karma item string
        if transaction.reasons:
            if len(transaction.reasons) > 1:
                reasons_plural = 's'
                reasons_has = 'have'
            else:
                reasons_plural = ''
                reasons_has = 'has'

            item_str += f' • **{transaction.name}** (new score is {karma_change.score}) and your reason{reasons_plural} {reasons_has} been recorded.\n'
        else:
            item_str += f' • **{transaction.name}** (new score is {karma_change.score}).\n'

    # Construct the reply string in totality
    # If you have error(s) and no items processed successfully
    if not item_str and error_str:
        reply = f'I couldn\'t karma the requested item{transaction_plural} because of the following problem{transaction_plural}:\n\n{error_str}'
    # If you have items processed successfully but some errors too
    elif item_str and error_str:
        reply = f'I have made changes to the following item(s) karma:\n{item_str}\nThere were some issues with the following item(s), too:\n\n{error_str}'
    # If all items were processed successfully
    else:
        reply = f'I have made changes to the following karma item{transaction_plural}:\n\n{item_str}'

    return reply.rstrip()
