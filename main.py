import utils
import os

# noinspection PyUnresolvedReferences
import emote_spam
# noinspection PyUnresolvedReferences
from tournament import tournament

print("Imports Done")


# When the bot logs in...
@utils.bot.listen("on_ready")
async def it_compiled_exclamation_point() -> None:
    print(f'We have logged in as {utils.bot.user}')  # ...Print that we have logged in.

print("Connecting to Discord...")

# Run the bot!
utils.bot.run(os.getenv("TOKEN"))
