import utils
# noinspection PyUnresolvedReferences
from utils import *

import json
import random
import disnake
from disnake.ext import tasks

from emotes import Emotes


@utils.bot.listen("on_ready")
async def start_spam():
    spam.start()  # ...start emote spam


@tasks.loop(minutes=15)
async def spam() -> None:
    for chan_id in utils.command_locations["spam"]:
        if random.randrange(0, 150) == 5:
            await utils.bot.get_channel(chan_id).send(Emotes.random_spam())

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Commands
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@setup_command.sub_command()
async def emote_spam(interaction: SlashInter) -> None:
    """
    Sets up your server to receive random emotes from Falinks Bot. Use this again to remove commands
    """
    await interaction.send(f"Thank you for adding {interaction.bot.user.mention} emote spam to your server! "
                           f"{Emotes.WHIMS}\nPlease select commands you would like to enable/disable, "
                           f"or select a channel for Falinks to occasionally send emotes to.",
                           view=EmoteSpamSetupSelector())


@synced_slash()
async def charge(interaction: SlashInter) -> None:
    """
    How big of a charge can we get?
    """
    charge.charge_count += 1
    s = ""
    for _ in range(charge.charge_count):
        s += Emotes.CHARGA_PET
    await interaction.send(s)


charge.charge_count = 0


@synced_slash()
async def random_spam(interaction: SlashInter) -> None:
    """
    Because why wait for the emote spam???
    """
    await interaction.send(Emotes.random_spam())


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Views
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Reference functions instead of just their str names here so if the
# functions change you are alerted to change them here too.
emote_commands = (charge, random_spam)


class EmoteSpamSetupSelector(disnake.ui.View):
    def __init__(self):
        super().__init__()

    # noinspection PyUnusedLocal
    # The channel_select allows the user to choose a channel that will periodically get sent random emotes from
    # Falinks Bot. If the channel was selected previously, selecting it again will remove it.
    @disnake.ui.channel_select(
        placeholder="Select an emote spam channel",
        channel_types=[disnake.ChannelType.text]
    )
    async def channel_callback(self, select: disnake.ui.ChannelSelect, interaction: ComponentInter) -> None:

        added = utils.toggle_object_in_list(utils.command_locations["spam"], int(interaction.values[0]))
        utils.command_locations.save()

        if added:
            await interaction.send(f"The channel <#{interaction.values[0]}> has been added to the spam list."
                                   f"Select that channel again using this command to remove it")
        else:
            await interaction.send(f"The channel <#{interaction.values[0]}> has been removed from the spam list.")

    # noinspection PyUnusedLocal
    # This selector allows the user to add or remove emote_spam-related commands from their server.
    @disnake.ui.string_select(
        placeholder="Chose commands to add",
        options=list(map(lambda sc: sc.name, emote_commands)),
        max_values=len(emote_commands)
    )
    async def command_choice_callback(self, select: disnake.ui.ChannelSelect, interaction: ComponentInter) -> None:
        added_dict = {}
        for v in interaction.values:
            added_dict[v] = await utils.toggle_command(interaction.guild, v)
        await interaction.send(f"The following commands have been toggled:\n```{json.dumps(added_dict, indent=1)}```")
