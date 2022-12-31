# Voting

## Structure
- `vote_types`: Classes to carry out a type of vote with DB interaction. Should not interact with Discord
   - `base_vote.py` is the only implemented so far
   - `stv_calc.py` will be used to implement STV.
- `discord_interfaces`: Handles the Discord side of the interaction
   - In attempts to separate from vote types, some Discord specific DB interaction is in here.
   - This also complicates the DB schema, but the aim was complete separation.

## Database
- `Vote`: main class for a single vote
    - `DiscordVote`
    - `DiscordVoteMessage` The Discord message(s) for the vote
- `VoteChoice`: An option to vote for in a vote
    - `DiscordVoteChoice`: Now mostly redundant, Discord specific info per choice
- `UserVote`: Records a vote by a user

## Quirks

- There is a semi-arbitrary limit of 256 options per vote. Discord only allows 25 buttons per message, so the voting options can be split between multiple messages.
- As Discord doesn't allow fetching an ephemeral message or checking if it is still visible, vote feedback is slightly jank
    - It records the ephemeral message last used, then edits that one to avoid spamming messages
    - However, we can't tell when the ephemeral message disappears, so uses My Votes button to create a new one as required.