# machma10

Machma10 is a Telegram bot that allows a group to track exercises and see where everyone is at
with their reps.

## Getting started

1. To deploy Machma10, you first need to have a Telegram Bot API token. Talk to the
   [BotFather](https://t.me/BotFather) to create a new bot.

2. Make a copy of `config-template.toml` and rename it to `config.toml`. Place the Telegram
   Bot API token into the file.

2. Install the bot by running `poetry install`.

3. Run the bot with `python3 -m machma.bot`

## Todo

* Migrate to SqlAlchemy
* Validate link passed to `/exercise`
* Case-insensitive exercise names
* Allow exercise renames
* Only count todos from since a user joined
