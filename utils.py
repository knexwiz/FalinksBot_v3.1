import functools
import json
import os
from enum import Enum
from json import JSONEncoder
import disnake
from disnake import Emoji, PartialEmoji
from disnake.ext import commands
from collections import UserDict, UserList

from typing import (
    Any,
    Union,
    Optional,
    Callable,
)

__all__ = [
    "synced_slash", "synced_user_command", "synced_message_command",
    "attach_button",
    "find",
    "SlashInter", "ComponentInter", "MesInter", "UserInter", "Param",
    "setup_command",
    "toggle_command"
]
bot = commands.InteractionBot()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Helper Functions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Literally here just to make imports easier for me to remember in other files
find = disnake.utils.find
SlashInter = disnake.ApplicationCommandInteraction
ComponentInter = disnake.MessageInteraction
MesInter = disnake.MessageCommandInteraction
UserInter = disnake.UserCommandInteraction
Param = commands.Param


def toggle_object_in_list(list_to_modify: list, object_to_toggle: object) -> bool:
    """Adds an object to a list if it isn't in the list, or removes an object from the list if it isn't in it.

    :param list_to_modify: The list you want to change
    :param object_to_toggle: The object you want to toggle the appearance of
    :return: Bool for whether the object is currently in the list after the function
    """
    if object_to_toggle in list_to_modify:
        list_to_modify.remove(object_to_toggle)
        return False
    else:
        list_to_modify.append(object_to_toggle)
        return True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# File Handling
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ConstantlySavedDict(UserDict):
    """A dict subclass that saves itself to a json file every time it is updated

    :param file_name: The existing json file to read initial data from and save changed data to
    """

    def __init__(self, file_name: str) -> None:
        self.file_name = file_name
        self._saving = False

        f = open(self.file_name, "r")
        mapping = json.loads(f.read())
        f.close()

        super().__init__(mapping)

        self._saving = True

    def __setattr__(self, key, value):
        if key in self.__dict__.keys() and key in self.data.keys():
            self[key] = value
            value = self[key]
        super().__setattr__(key, value)

    def __setitem__(self, key: Any, value: Any) -> None:
        if isinstance(value, dict):
            self.data[str(key)] = CSDChildDict(value, self)
        elif isinstance(value, list):
            self.data[str(key)] = CSDChildList(value, self)
        else:
            self.data[str(key)] = value
        self.save()

    def __getitem__(self, key: Any) -> Any:
        return self.data[str(key)]

    def dict_pop(self, key, default_=None):
        v = self.data.pop(str(key), default_)
        self.save()
        return v

    def save(self) -> None:
        """Call to manually cause this instance to save to it's json file
        """
        if self._saving:
            print("saving", self.file_name)
            j = json.dumps(self, indent=2, cls=UserDictEncoder)
            f = open(self.file_name, "w")
            f.write(j)
            f.close()

    @staticmethod
    def disable_save_during(func: Callable) -> Callable:
        """This decorator allows you to specify functions that update large amounts of data in the ConstantlySavedDict,
        this way the function will wait until the end to save to it's JSON file, to prevent writing to the same file
        many more times than necessary
        """
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            resume = self._saving
            self._saving = False
            result = func(self, *args, **kwargs)
            if resume:
                self._saving = True
                self.save()
            return result
        return wrapper


class CSDChildDict(UserDict):
    def __init__(self, mapping, parent):
        self.parent = parent
        super().__init__(mapping)

    def __setitem__(self, key: Any, value: Any):
        if isinstance(value, dict):
            self.data[str(key)] = CSDChildDict(value, self)
        elif isinstance(value, list):
            self.data[str(key)] = CSDChildList(value, self)
        else:
            self.data[str(key)] = value
        self.save()

    def __getitem__(self, key: Any):
        return self.data[str(key)]

    def __setattr__(self, key, value):
        if key in self.__dict__.keys() and key in self.data.keys():
            self[key] = value
            value = self[key]
        super().__setattr__(key, value)

    def dict_pop(self, key, default_=None):
        v = self.data.pop(str(key), default_)
        self.parent.save()
        return v

    def save(self):
        self.parent.save()


class CSDChildList(UserList):
    def __init__(self, iterable, parent):
        self.parent = parent
        super().__init__(self._validate_item(item) for item in iterable)

    def _validate_item(self, value):
        if isinstance(value, dict):
            return CSDChildDict(value, self)
        if isinstance(value, list):
            return CSDChildList(value, self)
        return value

    def save(self):
        self.parent.save()

    def __setitem__(self, index, item):
        self.data[index] = self._validate_item(item)
        self.save()

    def insert(self, index, item):
        self.data.insert(index, self._validate_item(item))
        self.save()

    def append(self, item):
        self.data.append(self._validate_item(item))
        self.save()

    def remove(self, item):
        self.data.remove(self._validate_item(item))
        self.save()

    def extend(self, other):
        if isinstance(other, type(self)):
            self.data.extend(other)
        else:
            self.data.extend(self._validate_item(item) for item in other)
        self.save()


class UserDictEncoder(JSONEncoder):
    def default(self, o):
        if (
            isinstance(o, UserDict)
            or isinstance(o, ConstantlySavedDict)
            or isinstance(o, CSDChildDict)
            or isinstance(o, CSDChildList)
        ):
            return o.data
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Decorators
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# When the bot sees that a button has been clicked...
@bot.listen("on_button_click")
async def attached_button_click(interaction: ComponentInter) -> None:
    # Check if that button has a command attached with @attach_button
    if interaction.component.custom_id in attach_button.listeners:
        # If it does, preform the attached command.
        await attach_button.listeners[interaction.component.custom_id](interaction)


# The above function handles listening for buttons created with the following attach_button decorator
def attach_button(
    *,
    style: disnake.ButtonStyle = disnake.ButtonStyle.secondary,
    label: Optional[str] = None,
    disabled: bool = False,
    emoji: Optional[Union[str, Emoji, PartialEmoji]] = None,
    row: Optional[int] = None
) -> Callable:
    """Decorator that attaches a button object to a function that can be accessed with func.button. Arguments for the
    decorator will be passed to the created button. A listener is included with the bot that will call the function
    when the button is clicked. The button's custom_id is automatically set to the functions name, so an exception
    will be raised if multiple functions with the same name use this decorator.

    :param style: The style of the button.
    :param label: The label of the button, if any.
    :param disabled: Whether the button is disabled.
    :param emoji: The emoji of the button, if available.
    :param row: The relative row this button belongs to. A Discord component can only have 5
        rows. By default, items are arranged automatically into those 5 rows. If you'd
        like to control the relative positioning of the row then passing an index is advised.
        For example, row=1 will show up before row=2. Defaults to ``None``, which is automatic
        ordering. The row number must be between 0 and 4 (i.e. zero indexed).
    :return: The function with a button attached
    """
    def decorator_attach_button(func):
        @functools.wraps(func)
        def wrapper_attach_button(*args, **kwargs):
            return func(*args, **kwargs)

        if func.__name__ in attach_button.listeners.keys():
            raise ValueError("Multiple functions with @attach_button have the same name.")

        wrapper_attach_button.button = disnake.ui.Button(style=style, custom_id=func.__name__, label=label,
                                                         disabled=disabled, emoji=emoji, row=row)
        attach_button.listeners[func.__name__] = wrapper_attach_button
        return wrapper_attach_button

    return decorator_attach_button


# this is where all the functions decorated with decorator_attach_button are kept track of,
# so we can listen to their buttons
attach_button.listeners = {}


def synced_command(bot_command_type):
    def command_decorators(*, admin: bool = False, is_global: bool = False, **slash_kwargs):
        def decorator(func):
            
            if "name" in slash_kwargs.keys():
                synced_command.command_names[func.__name__] = slash_kwargs["name"]
            else:
                synced_command.command_names[func.__name__] = func.__name__

            # if the is_global override is used, set the "guild_ids" to an empty list
            if is_global:
                slash_kwargs["guild_ids"] = None
            else:
                # if "guild_ids" are specified in kwargs, the saved sync information will extend those specified
                if "guild_ids" in slash_kwargs.keys():
                    slash_kwargs["guild_ids"].extend(get_guild_ids(func.__name__))
                else:
                    slash_kwargs["guild_ids"] = get_guild_ids(func.__name__)

            if admin:
                slash_kwargs["default_member_permissions"] = disnake.Permissions(manage_guild=True)

            return bot_command_type(**slash_kwargs)(func)

        return decorator
    return command_decorators


synced_command.command_names = {}
synced_slash = synced_command(bot.slash_command)
synced_user_command = synced_command(bot.user_command)
synced_message_command = synced_command(bot.message_command)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Command locations
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


default = int(os.getenv("FBTA"))
command_locations = ConstantlySavedDict("command locations.json")


def get_guild_ids(command_name: str) -> list:
    """Returns the list of guilds that a command should be synced to. Automatically adds the default command
    testing guild to this list.

    :param command_name: the name of the command to look up
    :return: The list of guild ids to sync the command to
    """
    # if the command isn't already in the list of commands,
    if command_name not in command_locations.keys() or command_locations[command_name] is None:
        command_locations[command_name] = []          # add it to the list with no additional guilds to sync
    return [default, *command_locations[command_name]]  # add the default guild id to the returned values


async def toggle_command(
        guild: disnake.Guild,
        slash_command: Union[Callable, str],
        *,
        only_add_remove: Union[None, bool] = None
) -> bool:
    """Re-syncs a command into a specified guild. Default is to toggle, but only_add_remove can be specified to not
    accidentally remove a command you want to keep or vice versa.


    :param guild: the discord guild you want the command added/removed to
    :param slash_command: the slash command you want added/removed
    :param only_add_remove: set to true to only add the command or false to only remove the command
    :return: Returns whether the command is now currently callable in the specified guild
    """
    if isinstance(slash_command, commands.InvokableSlashCommand):
        slash_command = slash_command.name
    else:
        slash_command = slash_command.__name__

    if not isinstance(guild, disnake.Guild):
        raise TypeError("The guild passed must be an instance of InvokableSlashCommand")

    # Find the command in the guild
    guild_command_list = await bot.fetch_guild_commands(guild.id)
    guild_command = find(lambda c: c.name == slash_command, guild_command_list)

    # Decide whether the command should or shouldn't be in the guild at the end of this.
    if only_add_remove is True or (only_add_remove is None and guild_command is None):
        # ~~ ADD COMMAND ~~

        # add command if it isn't there yet
        if guild_command is None:

            # Find the command in the default guild
            default_command_list = await bot.fetch_guild_commands(default)
            default_command = find(lambda c: c.name == synced_command.command_names[slash_command],
                                   default_command_list)

            if default_command is None:  # Error if the command doesn't exist anywhere
                for q in default_command_list:
                    print(q.name)
                raise AttributeError(f"Could not find slash command {slash_command} in the default guild")

            await bot.create_guild_command(guild.id, default_command)

        # Add command to the saved sync list
        if guild.id not in command_locations[slash_command]:
            command_locations[slash_command].append(guild.id)

        return True  # B/c command is there now

    else:
        # ~~ REMOVE COMMAND ~~

        # Remove command if necessary
        if guild_command is not None:
            await bot.delete_guild_command(guild.id, guild_command.id)

        # Remove command from saved sync list
        if guild.id in command_locations[slash_command]:
            command_locations[slash_command].remove(guild.id)

        return False  # B/c command isn't there now


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Base Slash Commands
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# noinspection PyUnusedLocal
@synced_slash(admin=True, is_global=True, name="setup")
async def setup_command(interaction: SlashInter) -> None:
    """
    Sets up your server to be able to use certain commands.
    """
    pass
