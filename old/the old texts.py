print("Starting...")

print("Loading imports...")
import disnake
from disnake.ext import commands, tasks
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random
from io import BytesIO
import requests
import json

print("  Packages loaded")
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
)

# This function turns a url to an image file into bytes that can be used to create an emote
def get_image_bytes(url):
    r = requests.get(url)
    if r.status_code in range(200, 299):
        img = BytesIO(r.content)
        b = img.getvalue()
    else:
        print(f'Something went wrong. Response: {r.status_code}')
    return b


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                                                                            #
#                                                                                            #
#                                         Constants                                          #
#                                                                                            #
#                                                                                            #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

# These are bunch of constants that need to be updated if you are using the bot yourself

draft_guild_id = 1008182519415459841  # Discord guild_id for your draft server
draft_sheet_key = "1kPgHIgC1iMazTXv4Enie8pAICy3Fx8S4r9VuqyBBJHk"  # Google sheets key
serious_channel_id = 1008255522882981888  # If you have a opt in channel, put it id here
matches_category_id = 1015388960853348453  # The cattegory that new match discusion channels should be put into
new_team_slot = 24  # the position new team roles should be added at
emote_guilds = [
    1128537807191806012,
    1126625155112775813,
    809527517835952190,
    1054186269405610076,
    1054185765233496085,
    1054184993146019942,
    1012176533084971038
]  # A list of guilds created by Spriing for saving pokemon sprite emotes, contact him for an updated list and to add your bot to them
mod_role_id = 1008439387576610856  # The role id for mods

# And these are role ids that need to be set up and changed:
silly_role_ids = {
    "brightpowdergang": 1008443638461771976,
    "eggyfan": 1008443999717163018
}
pronoun_role_ids = {
    "they/them": 1008443466851811452,
    "he/him": 1008443516495605860,
    "she/her": 1008443553392893964
}
interest_role_ids = {
    "Interested": 1121871040969187409,
    "Content Creator": 1008556943851409408,
    "Spectator": 1008555835049394246
}
player_role_id = 1019003780097912863
generic_role_ids = {**silly_role_ids, **interest_role_ids}

# Update with your draft rules
picks_per_tier = {"S": 2, "A": 2, "B": 2, "C": 2, "D": 2}
# Turn this on if signups are allowed currently
sign_ups_open = False

### Here is our bot!
bot = commands.Bot(
    command_prefix=
    '!',  # not nescacary given nothing here is currently using text commands
    intents=disnake.Intents.all(
    ),  # I should really update this to only have intents the bot actually uses....
    test_guilds=[draft_guild_id])

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                                                                            #
#                                                                                            #
#                                       Gspread Setup                                        #
#                                                                                            #
#                                                                                            #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

### You will need to setup
### https://docs.gspread.org/en/latest/oauth2.html
gspread_client = gspread.authorize(
    ServiceAccountCredentials.from_json_keyfile_name('gspread.json', [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]))
draft_sheet = gspread_client.open_by_key(draft_sheet_key)
team_sheet = draft_sheet.worksheet("Teams")
match_sheet = draft_sheet.worksheet("Matches")

taken_pokemon = {}


class Fancy_Row_Values():
    """
  This is a class for better readability when using data from google sheets.
  rowtypes: team, pokemon
  """

    __row_types = {
        "team": ["draft_num", "name", "code", "id", "image_url", "emote"],
        "pokemon": ["name", "dex", "tier"],
        "match": [
            "channel_id", "week", "team1_id", "team2_id", "team1_name",
            "team2_name", "team1_wins", "team2_wins"
        ]
    }

    def __init__(self, row_type: str, values_list: list):
        i = 0
        self.__type = row_type
        for key in Fancy_Row_Values.__row_types[row_type]:
            setattr(self, key, values_list[i])
            i += 1

    def __list__(self):
        l = []
        for key in Fancy_Row_Values.__row_types[self.__type]:
            l.append(self.__dict__[key])
        return l

    @property
    def kwargs(self):
        l = {}
        for key in Fancy_Row_Values.__row_types[self.__type]:
            l[key] = self.__dict__[key]
        return l


class Team():
    """This is a team

  Attributes:
    role (disnake.Role): The role associated with the team.
    name (str): The team name.
    id (int): The team id.
    draft_num (int): Which draft the team is participating in.
    code (str): The 3 or 4 leter code for the team
    sheet_index (int): Which row the team's information is on in the sheet
    image_url (str): The teams logo
    emote (str): Preformated emote version of the team
    roster (List[Pokemon]): A list of pokemon on this team.
    mention (str): Teams emote + role mention.
    """
    __teams_dict = {}

    @staticmethod
    def load_teams() -> None:
        global taken_pokemon
        taken_pokemon = {}

        for key in Team.__teams_dict.keys():
            del Team.__teams_dict[key]
            Team.__teams_dict.pop(key)

        i = 1
        for row in team_sheet.get_values():
            info = Fancy_Row_Values("team", row)

            roster = []
            d = int(info.draft_num)
            if d not in taken_pokemon.keys():
                taken_pokemon[d] = []
            j = 6
            while j < len(row):
                poke = Pokemon.get(row[j])
                if poke != None:
                    roster.append(poke)
                    taken_pokemon[d].append(poke)
                j += 1
            role = bot.get_guild(draft_guild_id).get_role(int(info.id))
            Team(role=role, sheet_index=i, roster=roster, **info.kwargs)

            i += 1

    @staticmethod
    def get(id: Union[int, str]) -> Union["Team", None]:
        """Gets a team from a role id"""
        if int(id) in Team.__teams_dict.keys():
            return Team.__teams_dict[int(id)]
        return None

    @staticmethod
    def all_teams() -> List["Team"]:
        """Gets a list of all the teams"""
        return Team.__teams_dict.values()

    @staticmethod
    def from_member(member: disnake.Member) -> Union["Team", None]:
        """Gets a member's team. If they have multiple team roles only the first will be returned"""
        for role in member.roles:
            if role.id in Team.__teams_dict.keys():
                return Team.__teams_dict[role.id]
        return None

    def __init__(self, role: disnake.Role, draft_num: int, code: str,
                 sheet_index: int, image_url: str, emote: str,
                 roster: List["Pokemon"], **kwargs):
        """
    parameters:
      roster: this is test

    """
        self.role = role
        self.draft_num = int(draft_num)
        self.code = code
        self.sheet_index = sheet_index
        self.roster = roster

        if emote == "no_emote":
            self.emote = ""
        else:
            self.emote = emote

        if image_url == "no_image":
            self.image_url = None
        else:
            self.image_url = image_url

        Team.__teams_dict[self.id] = self

    @property
    def id(self) -> int:
        return self.role.id

    @property
    def name(self) -> str:
        return self.role.name

    @property
    def mention(self) -> str:
        return self.emote + self.role.mention

    def add_pokemon(self, pokemon: "Pokemon") -> None:
        """Adds a pokemon to a team and appends its name to the draft sheet"""

        taken_pokemon[self.draft_num].append(pokemon)
        team_sheet.update_cell(self.sheet_index,
                               len(self.roster) + 7, pokemon.name)
        self.roster.append(pokemon)

    def swap_pokemon(self, remove_pokemon: "Pokemon",
                     add_pokemon: "Pokemon") -> None:
        """Switches a pokemon on the team."""

        taken_pokemon[self.draft_num].append(add_pokemon)
        taken_pokemon[self.draft_num].remove(remove_pokemon)
        team_sheet.update_cell(self.sheet_index,
                               self.roster.index(remove_pokemon) + 7,
                               add_pokemon.name)
        self.roster[self.roster.index(remove_pokemon)] = add_pokemon

    def __str__(self):
        return self.mention


class Pokemon():
    __pokemon_dict = {}

    @staticmethod
    def load_emotes():
        for guild_id in emote_guilds:
            for emote in bot.get_guild(guild_id).emojis:
                for poke in Pokemon.__pokemon_dict.values():
                    if emote.name.replace("_", "-") == poke.dex:
                        poke.__emote = str(emote)

    @staticmethod
    def full_list():
        return list(Pokemon.__pokemon_dict.values())

    @staticmethod
    def get(name: str) -> Union["Pokemon", None]:
        """Finds the pokemon with the given name."""
        if name.lower() in Pokemon.__pokemon_dict.keys():
            return Pokemon.__pokemon_dict[name.lower()]
        return None


    def __init__(self, name: str, dex: str, tier: str):
        self.name = name.title()
        self.dex = dex
        self.tier = tier.upper()
        self.islow = False
        if self.tier == "LOW":
            self.tier = "D"
            self.islow = True
        self.__emote = None

        Pokemon.__pokemon_dict[name.lower()] = self

    @property
    def image_url(self) -> str:
        return "https://www.serebii.net/pokemon/art/{}.png".format(self.dex)

    @property
    def mention(self) -> str:
        return str(self.__emote) + self.name

    async def fetch_emote(self) -> str:
        """Fetches this pokemon's emote"""
        if self.__emote == None:
            try:
                emote = await bot.get_guild(
                    emote_guilds[0]
                ).create_custom_emoji(name=self.dex.replace("-", "_"),
                                      image=get_image_bytes(self.image_url))
                self.__emote = str(emote)
            except:
                return "<:pokeball:1012180033198104657>"
        return self.__emote

    def __str__(self):
        return self.mention


print("Loading pokemon information...")
poke_sheet = draft_sheet.worksheet("Pokemon")
for row in poke_sheet.get_values():
    info = Fancy_Row_Values("pokemon", row)
    p = Pokemon(**info.kwargs)
print("  Pokemon loaded")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                                                                            #
#                                                                                            #
#                                         Bot Events                                         #
#                                                                                            #
#                                                                                            #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


### Things to do once the bot logs into to discord. Usually used for just log in
###   messages or when testing/setting things up
@bot.event
async def on_ready():
    print(f'  We have logged in as {bot.user}')
    ### call this once to do the initial connection to sheets
    print("Starting team load...")
    Team.load_teams()
    print("  Teams loaded")

    print("Starting pokemon emote load...")
    Pokemon.load_emotes()
    print("  Pokemon emotes loaded")
    emote_spam.start()

    print("Start up finished")


@bot.event
async def on_message_interaction(interaction):
    cid = interaction.component.custom_id

    if cid == "tour_signup":
        tour_dict = get_tour()

        if tour_dict["signup"] is not True:
            await interaction.send(
                f"Sign ups are closed",
                ephemeral=True)
            return

        if interaction.author.mention in tour_dict["members"].keys():
            view = disnake.ui.View()
            view.add_item(
                disnake.ui.Button(label="Please drop me",
                                  style=disnake.ButtonStyle.primary,
                                  custom_id="tour_cancel",
                                  emoji="<:poryY:1011496058620235900>"))
            await interaction.send(
                f"You are already signed up!.", view=view,
                ephemeral=True)
            return
        name = interaction.author.nick
        if name is None: name = interaction.author.global_name
        if name is None: name = interaction.author.name

        tour_dict["members"][interaction.author.mention] = {
            "name": name,
            "wins": 0,
            "loses": 0,
            "ties": 0,
            "byes": 0,
            "opponents": {}
        }
        save_tour(tour_dict)
        await interaction.send(
            f"{interaction.author.mention} has signed up for {tour_dict['name']}")

        view2 = disnake.ui.View()
        view2.add_item(
            disnake.ui.Button(label="Sign me up!",
                              style=disnake.ButtonStyle.primary,
                              custom_id="tour_signup",
                              emoji="<:marowak_coolguy:1008434753806016652>"))
        await interaction.channel.send(f"Signups for {tour_dict['name']} are going on right now!",
                                       view=view2)
        await interaction.message.delete()
        return


    if cid == "tour_cancel":
        tour_dict = get_tour()

        if tour_dict["signup"] is not True:
            await interaction.send(
                f"Sign ups are closed",
                ephemeral=True)
            return

        if interaction.author.mention not in tour_dict["members"].keys():
            await interaction.send(
                f"You are already dropped!",
                ephemeral=True)
            return

        tour_dict["members"].pop(interaction.author.mention)
        save_tour(tour_dict)
        await interaction.send(
            f"{interaction.author.mention} has dropped from {tour_dict['name']}")
        return

    if cid.startswith("tourrep"):
        tour_dict = get_tour()
        ismod = interaction.author.guild_permissions.manage_roles
        if interaction.author.mention not in tour_dict["members"].keys() and not ismod:
            await interaction.send(
                f"You aren't even playing in the tournament!",
                ephemeral=True)
            return
        p1 = f'<{interaction.content.split("> vs <",1)[0].split("<",1)[1]}>'
        p2 = f'<{interaction.content.split("> vs <",1)[1]}'
        print(p1, p2)
        if interaction.author.mention != p1 and interaction.author.mention != p2 and not ismod:
            await interaction.send(
                f"You aren't one of those players!",
                ephemeral=True)
            return

        wid = int(cid[8])
        if wid == 1:
            tour_dict["members"][p1]["wins"] += 1
            tour_dict["members"][p2]["loses"] += 1
            tour_dict["members"][p1]["opponents"][p2] = "2-0"
            tour_dict["members"][p2]["opponents"][p1] = "0-2"
        if wid == 2:
            tour_dict["members"][p1]["wins"] += 1
            tour_dict["members"][p2]["loses"] += 1
            tour_dict["members"][p1]["opponents"][p2] = "2-1"
            tour_dict["members"][p2]["opponents"][p1] = "1-2"
        if wid == 3:
            tour_dict["members"][p2]["wins"] += 1
            tour_dict["members"][p1]["loses"] += 1
            tour_dict["members"][p1]["opponents"][p2] = "1-2"
            tour_dict["members"][p2]["opponents"][p1] = "2-1"
        if wid == 4:
            tour_dict["members"][p2]["wins"] += 1
            tour_dict["members"][p1]["loses"] += 1
            tour_dict["members"][p1]["opponents"][p2] = "0-2"
            tour_dict["members"][p2]["opponents"][p1] = "2-0"
        if wid == 5:
            tour_dict["members"][p2]["ties"] += 1
            tour_dict["members"][p1]["ties"] += 1
            tour_dict["members"][p1]["opponents"][p2] = "0-0"
            tour_dict["members"][p2]["opponents"][p1] = "0-0"




        return

    ### My server has a dedicated channel for serious topics with additional user agreements
    ###   that need to be accepted be for joining. This is a good example for adding users
    ###   to a private channel without using a role to mannage it.
    if cid == "off-topic-serious":
        chan = bot.get_channel(serious_channel_id)
        await chan.set_permissions(interaction.author, view_channel=True)
        await interaction.send(
            f"You have been added to the {chan.mention} channel.",
            ephemeral=True)
        return


    team_mentions = list(
        map(lambda rrm: Team.get(rrm), interaction.message.raw_role_mentions))
    author_team = Team.from_member(interaction.author)

    if cid.startswith("report"):
        cell = match_sheet.find(str(interaction.channel.id), in_column=1)
        if cell.__class__ == None.__class__:
            await interaction.response.send_message(
                "This channel is not recognized as a match discusion channel",
                ephemeral=True)
            return
        info = Fancy_Row_Values("match", match_sheet.row_values(cell.row))
        if info.team1_id == cid[7:len(cid)]:
            winner = Team.get(info.team1_id)
            looser = Team.get(info.team2_id)
            score = ["2", cid[6]]
        else:
            winner = Team.get(info.team2_id)
            looser = Team.get(info.team1_id)
            score = [cid[6], "2"]

        match_sheet.update("G{r}:H{r}".format(r=cell.row), [score])

        view = disnake.ui.View()
        view.add_item(
            disnake.ui.Button(label="Close Channel",
                              style=disnake.ButtonStyle.red,
                              custom_id="close"))

        await interaction.message.edit(
            f"This match has been reported by {interaction.author.mention} as a 2-{cid[6]} win for {winner.mention} over {looser.mention}.\n*If there was an error use **/report** again. If there is a dispute use **/mod** to call a mod to the channel*",
            view=view)
        try:
            await interaction.send()
        except:
            pass
        return

    if cid == "close":
        if interaction.author.id in interaction.message.raw_mentions and interaction.author != interaction.guild.owner:
            await interaction.message.edit(
                "The player who reported the match can't close the channel")
            return
        await interaction.channel.delete()
        return

    ### Any interactions that require a matching team should be below here. Any that don't should be above.

    if not author_team in team_mentions:
        await interaction.send(
            f"You aren't on <@&{team_mentions[0]}>! Sneaky sneaky.....",
            ephemeral=True)
        return

    if cid.startswith("waiver"):
        remove_poke = Pokemon.get(interaction.component.label)
        add_poke = Pokemon.get(cid[7:len(cid)])
        author_team.swap_pokemon(remove_poke, add_poke)
        await remove_poke.fetch_emote()
        await add_poke.fetch_emote()
        await interaction.message.edit(
            f"{author_team} has made a waiver, dropping {remove_poke} and picking up {add_poke}", view=None)

    if cid == "ko_choice":
        ko_count_view = disnake.ui.View()
        ko_options = []
        while len(ko_options) < 10:
            ko_options.append(disnake.SelectOption(label=str(len(ko_options))))
        ko_count_view.add_item(
            disnake.ui.Select(custom_id="ko_count", options=ko_options))
        author_team.ko_list = interaction.values.copy(),
        author_team.ko_counts = []
        pokemon = Pokemon.get(author_team.ko_list[0][0])
        embed = disnake.Embed(description=f"KOs for {pokemon.name}")
        embed.set_thumbnail(pokemon.image_url)

        await interaction.message.edit(
            f"{author_team} has started reporting thier KOs.",
            view=ko_count_view,
            embed=embed)
        try:
            await interaction.send()
        except:
            pass

    if cid == "ko_count":
        author_team.ko_counts.append(int(interaction.values[0]))
        i = len(author_team.ko_counts)
        s = ""
        if i == 6:
            rows = []
            i = 0
            while i < 6:
                pokemon = Pokemon.get(author_team.ko_list[0][i])
                rows.append([pokemon.name, author_team.ko_counts[i]])
                e = await pokemon.fetch_emote()
                s += f"{e}{author_team.ko_counts[i]} "
                i += 1

            draft_sheet.worksheet("KOs").append_rows(rows)
            await interaction.message.edit(
                f"{author_team} has submited the folowing kos:\n{s}",
                view=None,
                embed=None)
            try:
                await interaction.send()
            except:
                pass

        else:
            ko_count_view = disnake.ui.View()
            ko_options = []
            while len(ko_options) < 10:
                ko_options.append(
                    disnake.SelectOption(label=str(len(ko_options))))
            ko_count_view.add_item(
                disnake.ui.Select(custom_id="ko_count", options=ko_options))
            pokemon = Pokemon.get(author_team.ko_list[0][i])
            embed = disnake.Embed(description=f"KOs for {pokemon.name}")
            embed.set_thumbnail(pokemon.image_url)
            await interaction.message.edit(view=ko_count_view, embed=embed)

            try:
                await interaction.send()
            except:
                pass



""""""  # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


#                                                                                            #
#                                                                                            #
#                                       Slash Commands                                       #
#                                                                                            #
#                                                                                            #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


### Signs a player up for the league.
@bot.slash_command()
async def signup(interaction,
                 team_name: str,
                 team_code: str,
                 team_color: str,
                 team_logo_url: str = "no_image",
                 team_emote_url: str = "no_emote"):
    """
  Signs you up for the league.

  Parameters
  ----------
  team_name: The name of your team.
  team_code: A 3 or 4 letter code for your team. Ex: Lilycove Spheals -> LCS
  team_color: The hex code for your teams color. Ex: fffbd8
  team_logo_url: A url link to your teams logo.
  team_emote_url: A url link to your teams emote image.
  """
    if sign_ups_open == False:
        await interaction.send(
            "Sign ups are currently not open.", ephemeral=True)
        return

    await interaction.send("working on signup...")

    ### check if the player already has a team role.
    team = Team.from_member(interaction.author)
    if team != None:
        await interaction.edit_original_response(
            f"You are already on the team {team}! You can't sign up again! *if you need to update your team information use /update_team.*")
        return

    ### will update when disnake fixes parms for strings. If this is still here i forgot ><
    if len(team_code) < 3 or len(team_code) > 4:
        await interaction.edit_original_response(
            "Your team code was the incorect length", ephemeral=True)
        return
    if len(team_color) != 6:
        await interaction.edit_original_response(
            "Your team color was not a 6 digit hexidecimal code",
            ephemeral=True)
        return

    tc = team_code.upper()
    for team in Team.all_teams():
        if team.code == tc:
            await interaction.edit_original_response(
                f"{tc} is already used as annother team's code. Please try again.",
                ephemeral=True)
            return
    if not tc.isalnum():
        await interaction.edit_original_response(
            "Your team code can only contain letters and numbers",
            ephemeral=True)
        return

    ### This is in a try/except block incase the color hex-code provided is invalid.
    try:
        c = disnake.Color(int(team_color, base=16))
    except:
        await interaction.edit_original_response(
            "There was an error with converting your hex code to a color",
            ephemeral=True)
        return

    ### If an emote was provided try to convert it into discord emote.
    te = "no_emote"
    if team_emote_url != "no_emote":
        try:
            emote = await interaction.guild.create_custom_emoji(
                name="__{}".format(tc), image=get_image_bytes(team_emote_url))
            te = str(emote)
        except:
            pass

    role = await interaction.guild.create_role(
        name=team_name, color=c,
        mentionable=True)  # make a new role with the info from the parameters
    await role.edit(position=new_team_slot)
    player_role = interaction.guild.get_role(player_role_id)
    await interaction.author.add_roles(role, player_role
                                       )  # give the player thier team's role

    irole = interaction.guild.get_role(interest_role_ids["Interested"])
    srole = interaction.guild.get_role(interest_role_ids["Spectator"])
    await interaction.author.remove_roles(irole, srole)

    team_sheet.append_row([1, team_name, tc,
                           str(role.id), team_logo_url,
                           te])  # add the team information to the spread sheet

    image = None if team_logo_url == "no_image" else team_logo_url

    new_team = Team(role=role,
                    draft_num=1,
                    code=tc,
                    sheet_index=len(Team.all_teams()) + 1,
                    image_url=image,
                    emote=te,
                    roster=[])

    await interaction.edit_original_response(
        f"{new_team} has signed up for the league!")


"""
"""


### Signs a player up for the league.
@bot.slash_command()
async def update_team(interaction,
                      new_name: str = "",
                      new_code: str = "",
                      new_color: str = "",
                      new_logo_url: str = "",
                      new_emote_url: str = ""):
    """
  Changes the information for your team. Leave information you want to keep the same blank.

  Parameters
  ----------
  new_name: The name of your team.
  new_code: A 3 or 4 letter code for your team. Ex: Lilycove Spheals -> LCS
  new_color: The hex code for your teams color. Ex: fffbd8
  new_logo_url: A url link to your teams logo.
  new_emote_url: A url link to your teams emote image.
  """
    ### check if the player already has a team role.
    team = Team.from_member(interaction.author)
    await interaction.send(f"working on team update...\n```{interaction.filled_options}```")
    if team == None:
        await interaction.edit_original_response(
            "You dont have a team yet. Use /signup to signup for the league if signups are active")
        return

    s = "Change log: ```diff"

    if new_name != "":
        s += f"\n+Team name changed from *{team.name}* to *{new_name}*."
        await team.role.edit(name=new_name)

    if new_code != "":
        tc = new_code.upper()
        if len(tc) < 3 or len(tc) > 4 or not tc.isalnum():
            s += f"\n-{new_code} is not a valid team code."
        else:
            fail = False
            for testteam in Team.all_teams():
                if testteam.code == tc:
                    fail = True
            if fail:
                s += f"\n-The team code {tc} is already taken."
            else:
                s += f"\n+Team code changed from {team.code} to {tc}."
                team.code = tc

    if new_color != "":
        if len(new_color) != 6:
            s += f"\n-{new_color} is not a valid color hex code."
        else:
            try:
                c = disnake.Color(int(new_color, base=16))
                await team.role.edit(color=c)
                s += "\n+Team color changed."
            except:
                s += f"\n-{new_color} is not a valid color hex code."

    if new_logo_url != "":
        s += "\n+Team logo updated."
        team.image_url = new_logo_url

    if new_emote_url != "":
        try:
            bits = get_image_bytes(new_emote_url)
            for emote in interaction.guild.emojis:
                if str(emote) == team.emote:
                    await emote.delete()
            emote = await interaction.guild.create_custom_emoji(
                name="__{}".format(team.code), image=bits)
            team.emote = str(emote)
            s += "\n+Team emote has been updated."
        except:
            s += "\n-There was an error with the new emote."

    team_sheet.update(
        'B{q}:F{q}'.format(q=team.sheet_index),
        [[team.name, team.code,
          str(team.id), team.image_url, team.emote]])

    await interaction.edit_original_response(
        f"{team} has updated thier team:\n {s}```")


"""
"""


@bot.slash_command()
async def team_roster(interaction, team_role: disnake.Role = None):
    """
  Displays all the pokemon on a team

  Parameters
  ----------
  team: Optional. Leaving blank will display your own team
  """
    ### check if the player already has a team role.
    if team_role == None:
        team = Team.from_member(interaction.author)
        if team == None:
            await interaction.response.send_message(
                "You dont have a team. Be sure to fill in the team_role parameter when using this command",
                ephemeral=True)
            return
    else:
        team = Team.get(team_role.id)
        if team == None:
            await interaction.response.send_message("That is not a valid team",
                                                    ephemeral=True)
            return
    el = ""
    for pokemon in team.roster:
        el += await pokemon.fetch_emote()
    embed = disnake.Embed(description=f"{team.role.mention}'s team roster",
                          color=team.role.color)
    embed.set_thumbnail(team.image_url)
    await interaction.response.send_message(el, embed=embed)


"""
"""


@bot.slash_command()
@commands.default_member_permissions(manage_roles=True)
async def reload_sheet(interaction):
    """
  Use only if you have made manual adjustments to the draft sheet google doc.
  """
    Team.load_teams()
    await interaction.response.send_message("It has been done.",
                                            ephemeral=True)


"""
"""
### These are for keeping track of the draft. pick_order is each team twice [A, B, C, C, B, A] so its a full snake and pick_index % len(pick_order) is used to figure out which team's turn it is.
pick_order = []
pick_index = 0
current_pick = lambda: pick_order[0] if pick_index == 0 else pick_order[
    pick_index % len(pick_order)]


### Command for
@bot.slash_command()
@commands.default_member_permissions(manage_roles=True)
async def start_draft(interaction, draft_number: int, start_index: int = 0):
    """
  Starts the draft!

  Parameters
  ----------
  draft_number: Which teams to include in the draft (column 1 on team sheet)
  start_index: Used if you need to resume a draft that was interupted
  """
    global pick_order, pick_index
    pick_order = []
    pick_index = start_index
    s = ""
    for team in Team.all_teams():
        if team.draft_num == draft_number:
            pick_order.append(team)
            s += f"\n{team}"
    r = pick_order.copy()
    r.reverse()
    pick_order.extend(r)

    await interaction.response.send_message(
        f"Draft {draft_number} has started!\nPick order: {s}")
    await interaction.channel.send(f"{current_pick()} it is your pick.")


"""
"""


@bot.slash_command()
async def pick(interaction, pokemon_name: str, override: bool = False):
    """
  Make your pick. The bot will tell you when its your turn.

  Parameters
  ----------
  pokemon_name: Make sure you spell corectly and forms go after pokemon name. ex: Exeggutor Alola
  override: can only be used by sprring so dont try
  """

    await interaction.send(f"working on pick...\n```{pokemon_name}```")
    global pick_index

    ### Error on draft not occuring
    if pick_order == []:
        await interaction.edit_original_response(
            "There isn't a draft happening right now...")
        return

    ### Get the member's team
    team = Team.from_member(interaction.author)
    if interaction.author.id == 478147906738847746 and override:
        team = current_pick()

    ### Error on member not having a team
    if team == None:
        await interaction.edit_original_response(
            "You dont have a team, you can't make picks.")
        return

    ### Error on out of turn pick attempt
    if team != current_pick():
        await interaction.edit_original_response("It's not your turn to pick.")
        return

    pokemon = Pokemon.get(pokemon_name)

    if pokemon_name == "random" and override:
        i = 0
        rt = list(picks_per_tier.keys())[i]
        found = False
        while not found:
            t = 0
            for check_poke in team.roster:
                if check_poke.tier == rt:
                    t += 1
            if t >= picks_per_tier[rt]:
                i += 1
                rt = list(picks_per_tier.keys())[i]
            else:
                found = True

        available = []
        for poke in Pokemon.full_list():
            if poke.tier == rt and poke not in taken_pokemon[team.draft_num] and poke.islow is False:
                available.append(poke)

        pokemon = random.choice(available)

    ### Error if the name param doesn't match a pokemon
    if pokemon is None:
        await interaction.edit_original_response(
            "{} is not a recognized pokemon name.".format(pokemon_name))
        return

    ### Error on the pokemon being on a different team
    if pokemon in taken_pokemon[team.draft_num]:
        await interaction.edit_original_response(
            "That pokemon has already been picked.")
        return

    ### Error if the pokemon's tier isnt in the pick_per_tier list (ie NOT LEGAL)
    if pokemon.tier not in picks_per_tier.keys():
        await interaction.edit_original_response(
            f"{pokemon.name} is not legal for this draft.")
        return

    t = 0
    for check_poke in team.roster:
        if check_poke.tier == pokemon.tier:
            t += 1

    ### Error on illegal pick based on tier restrictions
    if t >= picks_per_tier[pokemon.tier]:
        await interaction.edit_original_response(
            f"You already have too many {pokemon.tier} tier pokemon!.")
        return

    ### add pokemon to the team
    team.add_pokemon(pokemon)

    embed = disnake.Embed(description=f"{team} has picked {pokemon.name}!",
                          color=team.role.color)
    embed.set_thumbnail(pokemon.image_url)
    await interaction.edit_original_response(None, embed=embed)

    ### message the next team.
    pick_index += 1
    await interaction.channel.send(f"> {current_pick()} it is your turn to pick."
                                   )

    tiers = {}
    for t in picks_per_tier.keys():
        tiers[t] = []
    for poke in current_pick().roster:
        if poke.tier in tiers.keys():
            tiers[poke.tier].append(poke)

    s = "> "
    for t in tiers.keys():
        j = 0
        for poke in tiers[t]:
            s += await poke.fetch_emote()
            j += 1
        while j < picks_per_tier[t]:
            s += ":regional_indicator_{}:".format(t.lower())
            j += 1
    await interaction.channel.send(s)


"""
"""


@bot.slash_command()
@commands.default_member_permissions(manage_roles=True)
async def skip(interaction):
    """
  Make your pick. The bot will tell you when its your turn.

  Parameters
  ----------
  pokemon_name: Make sure you spell corectly and forms go after pokemon name. ex: Exeggutor Alola
  """

    global pick_index

    ### Error on draft not occuring
    if pick_order == []:
        await interaction.response.send_message(
            "There isn't a draft happening right now...", ephemeral=True)
        return

    await interaction.response.send_message(
        f"{current_pick()} has been skipped")

    ### message the next team.
    pick_index += 1
    await interaction.channel.send(f"{current_pick()} it is your turn to pick."
                                   )

    tiers = {}
    for t in picks_per_tier.keys():
        tiers[t] = []
    for poke in current_pick().roster:
        if poke.tier in tiers.keys():
            tiers[poke.tier].append(poke)

    s = ""
    for t in tiers.keys():
        j = 0
        for poke in tiers[t]:
            s += await poke.fetch_emote()
            j += 1
        while j < picks_per_tier[t]:
            s += ":regional_indicator_{}:".format(t.lower())
            j += 1
    await interaction.channel.send(s)


"""
"""


@bot.slash_command()
async def waiver(interaction, pokemon_you_want: str):
    """
  Changes a pokemon on your team. Contact a mod for trades.

  Parameters
  ----------
  pokemon_you_want: The pokemon you want to pick up. The bot will ask what pokemon you want to drop after.
  """

    ### Get the member's team
    team = Team.from_member(interaction.author)

    ### Error on member not having a team
    if team == None:
        await interaction.response.send_message(
            "You dont have a team, you can't make waivers.")
        return

    pokemon = Pokemon.get(pokemon_you_want)

    ### Error if the name param doesn't match a pokemon
    if pokemon == None:
        await interaction.response.send_message(
            f"{pokemon_you_want} is not a recognized pokemon name.")
        return

    ### Error on the pokemon being on a different team
    if pokemon in taken_pokemon[team.draft_num]:
        await interaction.response.send_message(
            "That pokemon is already on a different team. Ask a mod to preform a trade.")
        return

    ### Error if the pokemon's tier isnt in the pick_per_tier list (ie NOT LEGAL)
    if pokemon.tier not in picks_per_tier.keys():
        await interaction.response.send_message(
            f"{pokemon.name} is not legal for this draft.")
        return

    view = disnake.ui.View()
    i = 0
    for rpoke in team.roster:
        if rpoke.tier == pokemon.tier:
            e = await rpoke.fetch_emote()
            view.add_item(
                disnake.ui.Button(label=rpoke.name,
                                  style=disnake.ButtonStyle.primary,
                                  custom_id=f"waiver{i}{pokemon.name}",
                                  emoji=e))
            i += 1

    e = await pokemon.fetch_emote()
    await interaction.response.send_message(
        f"{team} has started a waiver to pick up the Pokémon {pokemon}. Which {pokemon.tier} tier pokemon would you like to drop for it?",
        view=view)


"""
"""

charge_count = 0
@bot.slash_command()
async def charge(interaction):
    """
  Because apparently you cant use animated emoji if you dont have nitro
  """
    global charge_count
    charge_count += 1
    s = ""
    i = 0
    while i < charge_count:
        s += "<a:charga_pet:1125849966896762950>"
        i += 1
    await interaction.response.send_message(s)

@bot.slash_command()
async def ko(interaction):
    """
  Count your KO's for the week.
  """

    ### Get the member's team
    team = Team.from_member(interaction.author)

    ### Error on member not having a team
    if team == None:
        await interaction.response.send_message(
            "You dont have a team, you can't count KO's.", ephemeral=True)
        return

    options = []

    for pokemon in team.roster:
        emote = await pokemon.fetch_emote()
        options.append(disnake.SelectOption(label=pokemon.name, emoji=emote))

    view = disnake.ui.View()
    view.add_item(
        disnake.ui.Select(custom_id="ko_choice",
                          options=options,
                          min_values=6,
                          max_values=6))

    await interaction.response.send_message(
        f"{team} has started reporting thier KOs. Select the pokemon you brought this week:",
        view=view)


"""
"""


@bot.slash_command()
@commands.default_member_permissions(manage_roles=True)
async def post_matches(interaction, week: int):
    """
  Posts all matches for the week.

  Parameters
  ----------
  week: The week to post.
  """
    postmatches.start(week=week)
    await interaction.response.send_message(
        f"Match channels for week {week} are being posted now. This will take a couple minutes."
    )


"""
"""


@bot.slash_command()
async def report(interaction):
    """
  Report your matches for the week.
  """  ##["channel_id", "week", "team1_id", "team2_id", "team1_name", "team2_name", "team1_wins", "team2_wins"]
    cell = match_sheet.find(str(interaction.channel.id), in_column=1)
    if cell.__class__ == None.__class__:
        await interaction.response.send_message(
            "This channel is not recognized as a match discusion channel",
            ephemeral=True)
        return

    info = Fancy_Row_Values("match", match_sheet.row_values(cell.row))
    team1 = Team.get(info.team1_id)
    team2 = Team.get(info.team2_id)

    view = disnake.ui.View()
    view.add_item(
        disnake.ui.Button(label=f"{team1.name} 2-0",
                          style=disnake.ButtonStyle.primary,
                          custom_id=f"report0{team1.id}",
                          emoji=None if team1.emote == "" else team1.emote))
    view.add_item(
        disnake.ui.Button(label=f"{team1.name} 2-1",
                          style=disnake.ButtonStyle.primary,
                          custom_id=f"report1{team1.id}",
                          emoji=None if team1.emote == "" else team1.emote))
    view.add_item(
        disnake.ui.Button(label=f"{team2.name} 2-0",
                          style=disnake.ButtonStyle.primary,
                          custom_id=f"report0{team2.id}",
                          emoji=None if team2.emote == "" else team2.emote))
    view.add_item(
        disnake.ui.Button(label=f"{team2.name} 2-1",
                          style=disnake.ButtonStyle.primary,
                          custom_id=f"report1{team2.id}",
                          emoji=None if team2.emote == "" else team2.emote))

    await interaction.response.send_message(
        f"We have started reporting for the match {team1.code} vs. {team2.code}\nWhich team won?",
        view=view)


"""
"""


@bot.slash_command()
async def mod(interaction, reason: str = ""):
    """
  Calls a mod to the match discusion channel.

  Parameters
  ----------
  reason: Use this so the mod knows why they were called to the channel.
  """
    cell = match_sheet.find(str(interaction.channel.id), in_column=1)
    if cell.__class__ == None.__class__:
        await interaction.response.send_message(
            "This channel is not recognized as a match discusion channel",
            ephemeral=True)
        return

    mod_role = interaction.guild.get_role(mod_role_id)
    await interaction.channel.set_permissions(mod_role, view_channel=True)

    s = f"{mod_role.mention} has been added to this channel!"

    if reason != "":
        s += f"\n\n{interaction.author.mention}'s reason for calling a mod:\n{reason}"

    await interaction.response.send_message(s)


"""
"""


@bot.slash_command()
@commands.default_member_permissions(manage_roles=True)
async def unmod(interaction):
    """
  Removes mods from the match discusion channel.
  """
    cell = match_sheet.find(str(interaction.channel.id), in_column=1)
    if cell.__class__ == None.__class__:
        await interaction.response.send_message(
            "This channel is not recognized as a match discusion channel",
            ephemeral=True)
        return

    mod_role = interaction.guild.get_role(mod_role_id)
    await interaction.channel.set_permissions(mod_role, view_channel=None)

    await interaction.response.send_message("The mods have left this channel")


"""
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                                                                            #
#                                                                                            #
#                                         tournament                                         #
#                                                                                            #
#                                                                                            #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

def get_tour ():
    f = open("tour.json", "r")
    j = json.loads(f.read())
    f.close()
    return j

def save_tour (d):
    f = open("tour.json", "w")
    f.write(json.dumps(d,indent=2))
    f.close()

@bot.slash_command()
@commands.default_member_permissions(manage_roles=True)
async def setup_tour(interaction, tour_name: str, challenge_command: str):
    """
  Warning: this will delete any other tour information.
  """
    if interaction.channel.id != 1151234664007225377:
        await interaction.send ("can't do that here",ephemeral=True)
        return

    await interaction.channel.purge()

    tour_dict = {
        "name": tour_name,
        "command": challenge_command,
        "signup": True,
        "members":{}
    }
    save_tour(tour_dict)
    view = disnake.ui.View()
    view.add_item(
        disnake.ui.TextInput(label="Sign me up!",
                          style=disnake.TextInputStyle.short,
                          custom_id="tour_signup",
                          placeholder="Your Team's Pokepaste Here"))

    await interaction.response.send_message(
        f"{interaction.author.mention} has started signups for {tour_name}!")
    await interaction.channel.send(f"Signups for {tour_name} are going on right now!",
        view=view)


@bot.slash_command()
@commands.default_member_permissions(manage_roles=True)
async def start_tour(interaction):
    tour_dict = get_tour()

    if interaction.channel.id != 1151234664007225377:
        await interaction.send ("can't do that here",ephemeral=True)
        return

    if tour_dict["signup"] is False:
        await interaction.send ("It's too late for that",ephemeral=True)
        return

    await interaction.channel.purge()

    await interaction.send(f"{tour_dict['name']} is starting! Working on posting round 1 pairings...")

    mems = list(tour_dict["members"].keys())
    random.shuffle(mems)
    i = 0
    while i < len(mems):
        if i+1 == len(mems):
            tour_dict["members"][mems[i]]["byes"] = 1
            await interaction.channel.send(f"{int(i/2+1)}. {mems[i]} == BYE")
        else:
            view = disnake.ui.View()
            view.add_item(
                disnake.ui.Button(label="2-0",
                                  style=disnake.ButtonStyle.primary,
                                  custom_id="tourrep 1"))
            view.add_item(
                disnake.ui.Button(label="2-1",
                                  style=disnake.ButtonStyle.primary,
                                  custom_id="tourrep 2"))
            view.add_item(
                disnake.ui.Button(label="1-2",
                                  style=disnake.ButtonStyle.primary,
                                  custom_id="tourrep 3"))
            view.add_item(
                disnake.ui.Button(label="0-2",
                                  style=disnake.ButtonStyle.primary,
                                  custom_id="tourrep 4"))
            view.add_item(
                disnake.ui.Button(label="Draw",
                                  style=disnake.ButtonStyle.primary,
                                  custom_id="tourrep 5"))
            await interaction.channel.send(f"{int(i/2+1)}. {mems[i]} vs {mems[i+1]}", view = view)
        i += 2
    tour_dict["signup"] = False
    save_tour(tour_dict)
    await interaction.channel.send(f"Remember to use the following command when challenging you opponents\n{tour_dict['command']}")



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                                                                            #
#                                                                                            #
#                                         bot.run :D                                         #
#                                                                                            #
#                                                                                            #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


### | 0          | 1    | 2        | 3        | 4     | 5     | 6          | 7
### | channel_id | week | team1_id | team_2id | team1 | team2 | team1_wins | team2_wins
@tasks.loop(seconds=60)
async def postmatches(week):
    print("matchthingyhappeningy")
    matches = map(lambda r: Fancy_Row_Values("match", r),
                  match_sheet.get_values())
    i = 0
    guild = bot.get_guild(draft_guild_id)
    for info in matches:
        i += 1
        if info.channel_id == "" and info.week.isdigit() and int(info.week) == week:
            team1 = Team.get(info.team1_id)
            team2 = Team.get(info.team2_id)
            chan = await guild.create_text_channel(
                name=f"{team1.code}-vs-{team2.code}",
                category=bot.get_channel(matches_category_id),
                overwrites={
                    team1.role:
                        disnake.PermissionOverwrite(view_channel=True),
                    team2.role:
                        disnake.PermissionOverwrite(view_channel=True),
                    guild.default_role:
                        disnake.PermissionOverwrite(view_channel=False)
                })
            e1, e2 = "", ""
            for pokemon in team1.roster:
                e1 += await pokemon.fetch_emote()
            for pokemon in team2.roster:
                e2 += await pokemon.fetch_emote()

            match_sheet.update_cell(i, 1, str(chan.id))
            await chan.send(
                f"This is the start of the match discusion channel for the week {week} match {team1.code} vs {team2.code}.\n\n{team1}\n{e1}\n\n{team2}\n{e2}\n\nUse /report to report your game after you are done."
            )
            return
    print("matchthingystoppeningy")
    postmatches.stop()


emotespams = [
    "<a:falinks:887379443822252082><a:falinks:887379443822252082>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920>",
    "<:tangela_shoes:1008434764417617920><:tangela_shoes:1008434764417617920><a:falinks:887379443822252082><a:falinks:887379443822252082>",
    "<:gyarados_scary:1008434755378884658><:gyarados_watergun1:1008434756842704906><:gyarados_watergun2:1008434758818205886>",
    "<:dracozolt_knife:1008434760768565339><:hungry_hungry_druddigon:1008434762798600202>",
    "<@!563579922807783465> <:eggytroll:1008434767659794532>",
    "<:eggytroll:1008434767659794532><:eggytroll:1008434767659794532><:eggytroll:1008434767659794532>",
    "<:happy_hax:1008436004115456000>",
    "<:hawlucha_thumpsup:1008434739969007726>",
    "<:marowak_coolguy:1008434753806016652>", "<:poryY:1011496058620235900>",
    "<:salazzle_smile:1008434752228962344>",
    "<:slowpoke_waawaa:1008434747044798564>",
    "<:snorlax_eatsleep_english:1008434745014763550>",
    "<:torkoal_angry:1008434741596397690>",
    "<:whimsicott_charm:1008434748756070530>",
    "<:gyarados_scary:1008434755378884658><:gyarados_watergun1:1008434756842704906><:gyarados_watergun2:1008434758818205886><:goodra_confusion:1008434750328930484>",
    "<:goodra_confusion:1008434750328930484>",
    "<a:charga_pet:1125849966896762950>",
    "<a:charga_pet:1125849966896762950>",
    "<a:charga_pet:1125849966896762950>",
    "<a:charga_pet:1125849966896762950><a:charga_pet:1125849966896762950>",
    "<a:charga_pet:1125849966896762950><a:charga_pet:1125849966896762950><a:charga_pet:1125849966896762950>",
    "<a:charga_pet:1125849966896762950><a:charga_pet:1125849966896762950><a:charga_pet:1125849966896762950><a:charga_pet:1125849966896762950><a:charga_pet:1125849966896762950>"
]


@tasks.loop(hours=1)
async def emote_spam():
    if random.randrange(0, 45) == 5:
        await bot.get_channel(1018998738502549634).send(
            random.choice(emotespams))


### Runs the bot. When hosting locally you can put your bot's token here instead of
###   os.getenv('TOKEN')

while True:
    print("Connecting to Discord...")
    bot.run()
    print("Disconected....")
