import utils
from utils import *
import random
import json
import disnake
from collections import UserDict
import os
from enum import Enum
import functools
import inspect

from emotes import Emotes

from typing import (
    Union,
    Self,
    List,
    Callable,
    Dict
)

accept_choices = ['SNOM', 'PIKA', 'EGGY', "DOZO", "PORY"]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# tournament Handler
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Phase(Enum):
    SIGNUP = "SIGNUP"
    BETWEEN_ROUNDS = "BETWEEN_ROUNDS"
    DURING_ROUND = "DURING_ROUND"
    TOP_CUT = "TOP_CUT"
    ENDED = "ENDED"


class Match(utils.CSDChildDict):
    def __init__(self, mapping, tour: "Tournament"):
        self.tour = tour
        super().__init__(mapping, tour)
        self.round_number: int = self["round_number"]
        self.table: int = self["table"]
        self.player_ids: List[int] = self["player_ids"]
        self.player_names: List[str] = self["player_names"]
        self.game_wins: List[int] = self["game_wins"]
        self.players: List["Player"] = []

        for pid in self.player_ids:
            self.players.append(tour.get_player(pid))

        for player in self.players:
            player.add_match(self)

    def report(self, scores: dict) -> list:
        score = [0, 0]
        for i, s in scores.items():
            if int(i) == self.player_ids[0]:
                score[0] = int(s)
            else:
                score[1] = int(s)
        self.game_wins = score
        return score

    def winner(self) -> Union["Player", None]:

        if self.game_wins is None or self.game_wins[0] == self.game_wins[1]:
            return None
        elif self.game_wins[0] >= self.game_wins[1]:
            return self.players[0]
        else:
            return self.players[1]


class Player(utils.CSDChildDict):
    def __init__(self, mapping, tour: "Tournament"):
        self.tour = tour
        super().__init__(mapping, tour)
        self.id: int = self["id"]
        self.name: str = self["name"]
        self.tag: str = self["tag"]
        self.paste: Union[str, None] = self["paste"]
        self.team_sheet: Union[str, None] = self["team_sheet"]
        self.dropped: bool = self["dropped"]
        self.byes: int = self["byes"]
        self._matches: List[Match] = []
        self.opponents: List[Self] = []

    def calc_score(self) -> int:
        return self.byes + sum([(1 if match.winner() is self else 0) for match in self._matches])

    def win_percentage(self) -> float:
        if len(self.opponents) == 0:
            return 1.0
        else:
            return self.calc_score() / (len(self._matches) + self.byes)

    def _mod_wp(self) -> float:
        wp = self.win_percentage()
        if wp < .25:
            return .25
        elif self.dropped and wp > .75:
            return .75
        else:
            return wp

    def calc_omw(self) -> float:
        if len(self.opponents) == 0:
            return 1.0
        else:
            return (sum([op._mod_wp() for op in self.opponents]) + (.25*self.byes)) / (len(self.opponents) + self.byes)

    def add_match(self, match: Match):
        if self in match.players:
            self._matches.append(match)
            op = find(lambda p: p is not self, match.players)
            if op not in self.opponents:
                self.opponents.append(op)

    def latest_match(self) -> Match:
        return self._matches[-1]

    def record_str(self) -> str:
        s = self.calc_score()
        return f"{s}-{(len(self._matches) + self.byes)-s}"


class Tournament(utils.ConstantlySavedDict):
    tour_dict: Dict[str, Self] = {}

    def __init__(self, guild_id: Union[int, str]):

        super().__init__(f"tournament\\tour{guild_id}.json")
        self._saving = False
        self.guild_id = guild_id
        self.name: str = self["name"]
        self.chan_id: int = self["chan_id"]
        self.challenge: str = self["challenge"]
        self.require_paste: bool = self["require_paste"]
        self.require_team_sheet: bool = self["require_team_sheet"]
        self.phase: Phase = Phase(self["phase"])
        self.current_round = self["current_round"]
        self.player_dict: Dict[str: Player] = self["players"]

        for player_id, player_dict in self["players"].items():
            self["players"][player_id] = Player(player_dict, self)

        self.match_list = utils.CSDChildList([], self)
        for match_dict in self["matches"]:
            self.match_list.append(Match(match_dict, self))
        self["matches"] = self.match_list

        Tournament.tour_dict[str(guild_id)] = self
        self._saving = True

    @classmethod
    def new(
            cls,
            *,
            guild_id: Union[int, str],
            chan_id: Union[int, str],
            name: str,
            challenge: str,
            require_paste: bool,
            require_team_sheet: bool
    ) -> Self:
        base = {
            "name": name,
            "chan_id": chan_id,
            "challenge": challenge,
            "require_paste": require_paste,
            "require_team_sheet": require_team_sheet,
            "phase": Phase.SIGNUP.value,
            "current_round": 0,
            "players": {},
            "matches": []
        }
        f = open(f"tournament\\tour{guild_id}.json", "w")
        f.write(json.dumps(base, indent=2))
        f.close()

        new_tour = cls(guild_id)

        return new_tour

    @classmethod
    def get_tour(cls, guild_id: Union[int, str]) -> Self:
        if str(guild_id) in cls.tour_dict:
            return cls.tour_dict[str(guild_id)]
        elif f"tour{guild_id}.json" in os.listdir("tournament"):
            return cls(guild_id)
        else:
            return None

    @classmethod
    def close(cls, tour: Self):
        cls.tour_dict.pop(str(tour.guild_id))
        os.remove(f"tournament\\tour{tour.guild_id}.json")
        del tour

    @utils.ConstantlySavedDict.disable_save_during
    def new_player(
            self,
            *,
            member: disnake.Member,
            tag: str,
            paste: Union[str, None],
            team_sheet: Union[str, None]
    ) -> Player:
        
        player = Player({
            "id": member.id,
            "name": member.display_name,
            "tag": tag,
            "byes": 0,
            "paste": paste,
            "team_sheet": team_sheet,
            "dropped": False
        }, self)

        self.player_dict[member.id] = player

        return player

    def remove_player(self, player_id) -> Union[UserDict, None]:
        return self.player_dict.dict_pop(player_id, False)

    def get_player(self, player_id: int) -> Union[Player, None]:
        if str(player_id) in self.player_dict.keys():
            return self.player_dict[str(player_id)]
        else:
            return None

    @utils.ConstantlySavedDict.disable_save_during
    def new_match(self, round_number: int, players: list[Player], table: int = 0) -> Match:
        if len(players) != 2:
            raise ValueError("Matches should have exactly two players")

        md = {
            "round_number": round_number,
            "player_ids": [],
            "player_names": [],
            "player_scores_before": [],
            "table": table,
            "game_wins": None
        }
        for p in players:
            if isinstance(p, Player):
                md["player_ids"].append(p.id)
                md["player_names"].append(p.name)
                md["player_scores_before"].append(p.calc_score())
            else:
                raise TypeError(f"The passed player {p} is not of a correct type")

        match = Match(md, self)
        self.match_list.append(match)

        return match

    def get_match(self, players: List[Player]) -> Union[Match, None]:

        if len(players) != 2:
            raise ValueError("Matches should have exactly two players")

        for match in self.match_list:
            if self.current_round != match.round_number:
                continue
            if players[0] not in match.players or players[1] not in match.players:
                continue
            return match
        return None

    @utils.ConstantlySavedDict.disable_save_during
    def swiss_round(self) -> List[Union[Match, Player]]:
        self.current_round += 1

        player_list: List[Player] = []

        for player in self.player_dict.values():
            if not player.dropped:
                player_list.append(player)

        def forbidden_count(play: Player):
            fc = 0
            for op in play.opponents:
                if op.dropped is False and op.calc_score() == play.calc_score():
                    fc += 1
            return fc

        random.shuffle(player_list)
        player_list.sort(key=lambda p: forbidden_count(p), reverse=True)
        player_list.sort(key=lambda p: p.byes, reverse=True)
        player_list.sort(key=lambda p: p.calc_score(), reverse=True)

        new_matches: List[Union[Match, Player]] = []

        while len(player_list) >= 2:
            player = player_list[0]
            for opponent in player_list[1:]:
                if opponent not in player.opponents:
                    new_matches.append(self.new_match(self.current_round, [player, opponent]))
                    player_list.remove(player)
                    player_list.remove(opponent)
                    break
            if player in player_list:
                opponent = player_list[1]
                new_matches.append(self.new_match(self.current_round, [player, opponent]))
                player_list.remove(player)
                player_list.remove(opponent)

        if len(player_list) == 1:
            player = player_list[0]
            player.byes += 1
            new_matches.append(player)

        return new_matches

    @utils.ConstantlySavedDict.disable_save_during
    def top_cut(self, num_players: int) -> List[Union[Match]]:
        self.current_round += 1

        player_list: List[Player] = []

        for player in self.player_dict.values():
            if not player.dropped:
                player_list.append(player)

        random.shuffle(player_list)
        player_list.sort(key=lambda p: p.calc_omw(), reverse=True)
        player_list.sort(key=lambda p: p.calc_score(), reverse=True)

        player_list = player_list[:num_players]

        new_matches: List[Union[Match, Player]] = []

        i = 0
        while len(player_list) >= 2:
            i += 1
            player = player_list[0]
            opponent = player_list[-1]
            new_matches.append(self.new_match(self.current_round, [player, opponent], table=i))
            player_list.remove(player)
            player_list.remove(opponent)

        return new_matches

    @utils.ConstantlySavedDict.disable_save_during
    def next_cut(self) -> List[Union[Match]]:
        last_round: List[Match] = []
        for match in self.match_list:
            if match.round_number == self.current_round:
                last_round.append(match)
        last_round.sort(key=lambda m: m.table)

        player_list: List[Player] = []

        for match in last_round:
            player_list.append(match.winner())

        self.current_round += 1

        new_matches: List[Union[Match]] = []

        i = 0
        while len(player_list) >= 2:
            i += 1
            player = player_list[0]
            opponent = player_list[-1]
            new_matches.append(self.new_match(self.current_round, [player, opponent], table=i))
            player_list.remove(player)
            player_list.remove(opponent)

        return new_matches

    def winner(self) -> Player:
        if self.phase == Phase.BETWEEN_ROUNDS:
            player_list: List[Player] = []

            for player in self.player_dict.values():
                if not player.dropped:
                    player_list.append(player)

            random.shuffle(player_list)
            player_list.sort(key=lambda p: p.calc_omw(), reverse=True)
            player_list.sort(key=lambda p: p.calc_score(), reverse=True)

            return player_list[0]

        elif self.phase == Phase.TOP_CUT:
            last_round: List[Match] = []
            for match in self.match_list:
                if match.round_number == self.current_round:
                    last_round.append(match)
            last_round.sort(key=lambda m: m.table)

            return last_round[0].winner()
        else:
            return random.choice(self.player_dict.values())


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Command Syncing
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

phased_commands: List[Callable] = []


def command_phases(
        *phases: Phase,
        any_channel: bool = False,
        extra_check: Callable[[Tournament], bool] = lambda tour: True
):
    def phase_decorator(func):
        @functools.wraps(func)
        async def check_phase_first(interaction: SlashInter, *args, **kwargs):
            tour = Tournament.get_tour(interaction.guild.id)

            if tour is None:
                await interaction.send("There seems to be no tournament for this server.", ephemeral=True)
                return

            if (not any_channel) and interaction.channel.id != tour.chan_id:
                await interaction.send("This is not the place for that.", ephemeral=True)
                return

            if tour.phase not in phases:
                await interaction.send("This is not the time for that.", ephemeral=True)
                return

            await func(tour, interaction, *args, **kwargs)
        sig = inspect.signature(check_phase_first)
        sig = sig.replace(parameters=tuple(sig.parameters.values())[1:])
        check_phase_first.__signature__ = sig
        phased_commands.append(func)
        func.phases = phases
        func.extra_check = extra_check
        return check_phase_first
    return phase_decorator


async def sync_to_phase(tour: Tournament, phase: Phase, guild: disnake.Guild):
    tour.phase = phase
    for com in phased_commands:
        # noinspection PyUnresolvedReferences
        await toggle_command(guild, com, only_add_remove=(phase in com.phases and com.extra_check(tour)))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Tournament Setup/Signup
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@setup_command.sub_command()
async def tournament(interaction: SlashInter):
    """
    Set up a swiss style tournament.
    """
    await interaction.response.send_modal(TournamentSetupModal())


class TournamentSetupModal(disnake.ui.Modal):
    def __init__(self):
        self.accept = random.choice(accept_choices)

        components = [
            disnake.ui.TextInput(
                label="Tournament Name",
                placeholder="No-name Cup",
                custom_id="name",
                style=disnake.TextInputStyle.short,
                max_length=50
            ),
            disnake.ui.TextInput(
                label="Challenge Command or Rule Set",
                placeholder="Challenge command or the name of the correct ruleset. "
                            "Use {tag} as an opponent name placeholder.",
                custom_id="challenge",
                style=disnake.TextInputStyle.long,
                max_length=500,
                required=False
            ),
            disnake.ui.TextInput(
                label="Require Full Team Sheet",
                placeholder="Type 'Y' if you would like to require a full team sheet. "
                            "These will not be visible to players",
                custom_id="require_paste",
                style=disnake.TextInputStyle.long,
                max_length=1,
                required=False
            ),
            disnake.ui.TextInput(
                label="Require Open Team Sheet",
                placeholder="Type 'Y' if you would like to require an open team sheet. "
                            "These will be visible to players.",
                custom_id="require_team_sheet",
                style=disnake.TextInputStyle.long,
                max_length=1,
                required=False
            ),
            disnake.ui.TextInput(
                label=f"Type '{self.accept}' once you have read the following:",
                placeholder="This command will delete all messages in this channel to use it as the hub for the"
                            "tournament.",
                custom_id="accept",
                style=disnake.TextInputStyle.long,
                max_length=4,
                min_length=4
            )
        ]

        super().__init__(
            title="tournament Setup",
            components=components
        )

    async def callback(self, interaction):
        if interaction.text_values["accept"] != self.accept:
            await interaction.send("You did not enter in the correct accept key acknowledging that the tournament set "
                                   "up would delete all messages in this channel. Please try again.",
                                   ephemeral=True)
            return

        await interaction.channel.purge()

        challenge = interaction.text_values["challenge"]
        require_paste = interaction.text_values["require_paste"].upper() == "Y"
        require_team_sheet = interaction.text_values["require_team_sheet"].upper() == "Y"

        tour = Tournament.new(
            guild_id=interaction.guild.id,
            chan_id=interaction.channel.id,
            challenge=challenge,
            require_paste=require_paste,
            require_team_sheet=require_team_sheet,
            name=interaction.text_values["name"]
        )

        await interaction.send(f"{interaction.author.mention} has started signups for {tour.name}!")

        view = disnake.ui.View()
        view.add_item(tournament_signup.button)
        await interaction.channel.send(f"## Signups for {tour.name} are going on right now!", view=view)

        await sync_to_phase(tour, Phase.SIGNUP, interaction.guild)


@attach_button(label="Sign me up!", emoji=Emotes.MAROWAK, style=disnake.ButtonStyle.blurple)
async def tournament_signup(interaction: ComponentInter):
    tour = Tournament.get_tour(interaction.guild.id)
    if tour.phase != Phase.SIGNUP:
        await interaction.send("This tournament is not accepting signups anymore.", ephemeral=True)
        return

    if str(interaction.author.id) in tour.player_dict.keys():
        components = [cancel_signup.button]
        if tour.require_paste or tour.require_team_sheet:
            components.append(change_team.button)
        await interaction.send(f"Are you sure you want to drop from {tour.name}? ):",
                               components=components,
                               ephemeral=True)
    else:
        await interaction.response.send_modal(SignupModal(tour))


@attach_button(label="Change My Team", style=disnake.ButtonStyle.green)
async def change_team(interaction: ComponentInter):
    tour = Tournament.get_tour(interaction.guild.id)
    await interaction.response.send_modal(ChangTeamModal(tour))


@attach_button(label="Drop Me Please", style=disnake.ButtonStyle.red)
async def cancel_signup(interaction: ComponentInter):
    tour = Tournament.get_tour(interaction.guild.id)
    tour.remove_player(interaction.author.id)
    await interaction.send("You have been dropped", ephemeral=True)
    await interaction.channel.send(f"{interaction.author.mention} has decided not to play in {tour.name}. ):")


class SignupModal(disnake.ui.Modal):
    def __init__(self, tour: Tournament):
        components = [
            disnake.ui.TextInput(
                label="Username",
                placeholder="Your IGN or Showdown Username",
                custom_id="tag",
                style=disnake.TextInputStyle.short,
                max_length=50
            )
        ]

        if tour.require_paste:
            components.append(
                disnake.ui.TextInput(
                    label="Team Paste",
                    placeholder="A url link to your team's full information (including EVs). "
                                "This won't be shown to opponents.",
                    custom_id="paste",
                    style=disnake.TextInputStyle.long,
                    max_length=500
                )
            )

        if tour.require_team_sheet:
            components.append(
                disnake.ui.TextInput(
                    label="Open Team Sheet",
                    placeholder="A url link to your open team sheet using the TO specified rules. "
                                "This will be shown to opponents.",
                    custom_id="team_sheet",
                    style=disnake.TextInputStyle.long,
                    max_length=500
                )
            )

        super().__init__(
            title="Sign Up!",
            components=components
        )

    async def callback(self, interaction: disnake.ModalInteraction):
        tour = Tournament.get_tour(interaction.guild.id)

        s = "Your signup has been accepted!"

        if "paste" in interaction.text_values.keys():
            paste = interaction.text_values["paste"]
            s += "\nPaste:\n" + paste
        else:
            paste = None

        if "team_sheet" in interaction.text_values.keys():
            team_sheet = interaction.text_values["team_sheet"]
            s += "\nTeam Sheet:\n" + team_sheet
        else:
            team_sheet = None

        tour.new_player(
            member=interaction.author,
            tag=interaction.text_values["tag"],
            paste=paste,
            team_sheet=team_sheet
        )

        await interaction.send(s, ephemeral=True)
        await interaction.channel.send(f"{interaction.author.mention} has signed up for {tour.name}!")

        view = disnake.ui.View()
        view.add_item(tournament_signup.button)
        await interaction.channel.send(f"## Signups for {tour.name} are going on right now!", view=view)

        await interaction.message.delete()


class ChangTeamModal(disnake.ui.Modal):
    def __init__(self, tour: Tournament):
        components = []

        if tour.require_paste:
            components.append(
                disnake.ui.TextInput(
                    label="Team Paste",
                    placeholder="A url link to your team's full information (including EVs). "
                                "This won't be shown to opponents.",
                    custom_id="paste",
                    style=disnake.TextInputStyle.long,
                    max_length=500
                )
            )

        if tour.require_team_sheet:
            components.append(
                disnake.ui.TextInput(
                    label="Open Team Sheet",
                    placeholder="A url link to your open team sheet using the TO specified rules. "
                                "This will be shown to opponents.",
                    custom_id="team_sheet",
                    style=disnake.TextInputStyle.long,
                    max_length=500
                )
            )

        super().__init__(
            title="Team Change",
            components=components
        )

    async def callback(self, interaction: disnake.ModalInteraction):
        tour = Tournament.get_tour(interaction.guild.id)
        player = tour.get_player(interaction.author.id)

        s = "Your team change has been accepted!"

        if "paste" in interaction.text_values.keys():
            player.paste = interaction.text_values["paste"]
            s += "\nPaste:\n" + player.paste

        if "team_sheet" in interaction.text_values.keys():
            player.team_sheet = interaction.text_values["team_sheet"]
            s += "\nTeam Sheet:\n" + player.team_sheet

        await interaction.send(s, ephemeral=True)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Tournament Rounds
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@synced_slash(admin=True)
@command_phases(Phase.SIGNUP)
async def tournament_end_signup(tour: Tournament, interaction: SlashInter):
    """
    This ends the signup phase for the tournament.
    """
    player_names = [player.name for player in tour.player_dict.values()]

    player_names.sort()

    s = "# Signups have ended!\n\n### Players:"
    for i, p in enumerate(player_names):
        s += "\n" + f"> {i}. {p}"

    s += "\n\nUse /tournament_start_next_round to start the first round."

    await interaction.channel.purge()
    await interaction.send(s)

    await sync_to_phase(tour, Phase.BETWEEN_ROUNDS, interaction.guild)


@synced_slash(admin=True)
@command_phases(Phase.BETWEEN_ROUNDS)
async def tournament_start_next_round(tour: Tournament, interaction: SlashInter):
    """
    Start the next round of the tournament.
    """

    await interaction.send("Working on Pairings.", ephemeral=True)

    new_matches = tour.swiss_round()

    await interaction.channel.send(f"# Pairings for round {tour.current_round}:")

    view = disnake.ui.View()
    view.add_item(report_score.button)

    for i, mp in enumerate(new_matches):
        if isinstance(mp, Player):
            await interaction.channel.send(
                f"{i+1}. <@{mp.id}> ({mp.calc_score() - 1}) "
                f"-- BYE"
            )
        else:
            await interaction.channel.send(
                f"{i+1}. <@{mp.players[0].id}> ({mp.players[0].calc_score()}) "
                f"vs <@{mp.players[1].id}> ({mp.players[1].calc_score()})",
                view=view
            )

    await sync_to_phase(tour, Phase.DURING_ROUND, interaction.guild)


@synced_slash(admin=True)
@command_phases(Phase.BETWEEN_ROUNDS, Phase.DURING_ROUND)
async def tournament_add_match(tour: Tournament, interaction: SlashInter,
                               player1: disnake.Member, player2: disnake.Member):
    """
    Start the next round of the tournament.
    """

    p1 = tour.get_player(player1.id)
    p2 = tour.get_player(player2.id)

    if player1 is None or player2 is None:
        await interaction.send("Couldn't find players for both of those users.", ephemeral=True)
        return

    await interaction.send("Working on add_match.", ephemeral=True)

    if tour.phase == Phase.BETWEEN_ROUNDS:
        tour.phase = Phase.DURING_ROUND
        tour.current_round += 1
        await interaction.channel.send(f"# Pairings for round {tour.current_round}:")

    new_match = tour.new_match(tour.current_round, [p1, p2])

    view = disnake.ui.View()
    view.add_item(report_score.button)

    await interaction.channel.send(
        f"<@{new_match.players[0].id}> ({new_match.players[0].calc_score()}) "
        f"vs <@{new_match.players[1].id}> ({new_match.players[1].calc_score()})",
        view=view
    )

    if tour.phase == Phase.BETWEEN_ROUNDS:
        await sync_to_phase(tour, Phase.DURING_ROUND, interaction.guild)


@attach_button(style=disnake.ButtonStyle.blurple, label="Report Score")
async def report_score(interaction: ComponentInter):
    if interaction.author not in interaction.message.mentions and not interaction.author.guild_permissions.manage_guild:
        await interaction.send("You can't report other player's matches", ephemeral=True)
        return
    tour = Tournament.get_tour(interaction.guild.id)
    match = tour.get_match([tour.get_player(mention.id) for mention in interaction.message.mentions])
    if match is None:
        await interaction.send("The match couldn't be found.", ephemeral=True)
    else:
        await interaction.response.send_modal(ReportScoreModal(match, interaction.message))


class ReportScoreModal(disnake.ui.Modal):
    def __init__(self, match, message):
        components = [
            disnake.ui.TextInput(
                label=f"{player.name}'s Game Wins",
                placeholder="0",
                custom_id=player.id,
                style=disnake.TextInputStyle.short,
                max_length=2
            ) for player in match.players
        ]

        self.match = match
        self.message = message

        super().__init__(
            title="Report Score",
            components=components
        )

    async def callback(self, interaction: disnake.ModalInteraction):
        for v in interaction.text_values.values():
            if not v.isdigit():
                await interaction.send("One of the scores you entered was not a number: " + v, ephemeral=True)
                return
        games = self.match.report(interaction.text_values)

        await interaction.send("You have reported the match", ephemeral=True)
        s = f"{self.message.content} | *reported by {interaction.author.display_name}: {games[0]}-{games[1]}*"
        new_message = await self.message.edit(s, view=None)

        if not interaction.author.guild_permissions.manage_guild:
            m = await interaction.guild.fetch_member(
                self.match.players[1].id if self.match.players[0].id == interaction.author.id
                else self.match.players[0].id
            )
            await m.send(s + "\n" + "You may dispute this result for up to 15 minutes",
                         view=DisputeView(self.match, new_message))


class DisputeView(disnake.ui.View):
    def __init__(self, match: Union[UserDict, dict], message: disnake.Message):
        self.match = match
        self.message = message
        super().__init__()

    # noinspection PyUnusedLocal
    @disnake.ui.button(
        label="Dispute",
        style=disnake.ButtonStyle.red
    )
    async def dispute_callback(self, button, interaction: ComponentInter):
        s = self.message.content + " | \\**disputed\\**"
        await self.message.channel.send("A match has been disputed", reference=self.message)
        await self.message.edit(s)
        await interaction.send("Your dispute has been noted, please contact the TO")
        await interaction.message.edit(view=None)


@synced_message_command(admin=True, name="Report Match Result")
@command_phases(Phase.DURING_ROUND)
async def tournament_report_match(tour: Tournament, interaction: MesInter, message: disnake.Message):
    if len(message.mentions) != 2:
        await interaction.send("This message does not contain match data.", ephemeral=True)
        return
    match = tour.get_match([tour.get_player(mention.id) for mention in message.mentions])
    if match is None:
        await interaction.send("The match couldn't be found.", ephemeral=True)
    else:
        await interaction.response.send_modal(ReportScoreModal(match, message))


@synced_slash(admin=True)
@command_phases(Phase.DURING_ROUND)
async def tournament_end_round(tour: Tournament, interaction: SlashInter):
    """
    End a round of the tournament after all matches have been correctly reported
    """
    for match in tour.match_list:
        if match.round_number == tour.current_round and match.game_wins is None:
            await interaction.send(
                "There are still unreported matches, are you sure you want to end the round now?"
                " This will make the unreported matches count as losses for both players.",
                components=[end_round_warning.button],
                ephemeral=True
            )
            return
    await end_round_procedure(tour, interaction)


@attach_button(style=disnake.ButtonStyle.red, label="END THE ROUND")
async def end_round_warning(interaction: ComponentInter):
    await end_round_procedure(Tournament.get_tour(interaction.guild_id), interaction)


async def end_round_procedure(tour: Tournament, interaction):
    players_list: List[Player] = []

    for player in tour.player_dict.values():
        if not player.dropped:
            players_list.append(player)

    players_list.sort(key=lambda pl: pl.name)
    players_list.sort(key=lambda pl: pl.calc_omw(), reverse=True)
    players_list.sort(key=lambda pl: pl.calc_score(), reverse=True)

    if tour.current_round >= 3:
        s = ("# Round {} has ended!\n\n### Scores:\n```"
             "~~~~| Name            |  W | OMW% \n"
             "----+-----------------+----+------").format(tour.current_round)
        for i, player in enumerate(players_list):
            s += "\n{index:>3} | {name:<15} | {score:>2} | {omw:.1%}".format(
                index=i+1, name=player.name, score=player.calc_score(), omw=player.calc_omw())
    else:
        s = ("# Round {} has ended!\n\n### Scores:\n```"
             "~~~~| Name            |  W \n"
             "----+-----------------+----").format(tour.current_round)
        for i, player in enumerate(players_list):
            s += "\n{index:>3} | {name:<15} | {score:>2} ".format(
                index=i+1, name=player.name, score=player.calc_score())

    s += ("```\n\nUse /tournament_start_next_round to start the next round"
          " or /tournament_final_standings to end the tournament or continue to top cut.")

    await interaction.channel.purge()
    await interaction.send(s)

    tour.phase = Phase.BETWEEN_ROUNDS
    await sync_to_phase(tour, Phase.BETWEEN_ROUNDS, interaction.guild)


@synced_slash()
@command_phases(Phase.SIGNUP, Phase.DURING_ROUND, Phase.BETWEEN_ROUNDS, any_channel=True)
async def tournament_drop_from_tournament(tour: Tournament, interaction: SlashInter):
    """
    Drop from the tournament.
    """
    player = tour.get_player(interaction.author.id)
    if player is None:
        await interaction.send(f"You don't seem to be in {tour.name}...", ephemeral=True)
    elif player.dropped:
        await interaction.send(f"You are already dropped from {tour.name}", ephemeral=True)
    else:
        await interaction.send(
            f"Are you sure you want to drop from {tour.name}?",
            ephemeral=True,
            components=[drop_warning.button]
        )


@synced_user_command(admin=True, name="Tour Drop Player")
@command_phases(Phase.SIGNUP, Phase.BETWEEN_ROUNDS, Phase.DURING_ROUND)
async def tournament_drop_player_from_tournament(tour: Tournament, interaction: UserInter, user: disnake.User):
    player = tour.get_player(user.id)
    if player is None:
        await interaction.send(f"{user.mention} doesn't seem to be in {tour.name}...", ephemeral=True)
    elif player.dropped:
        await interaction.send(f"{user.mention} is already dropped from {tour.name}", ephemeral=True)
    else:
        await interaction.send(
            f"Are you sure you want to drop {user.mention} from {tour.name}?",
            ephemeral=True,
            components=[drop_warning.button])


@attach_button(style=disnake.ButtonStyle.red, label="DROP")
async def drop_warning(interaction: ComponentInter):
    tour = Tournament.get_tour(interaction.guild_id)

    if len(interaction.message.mentions) == 0:
        player = tour.get_player(interaction.author.id)
    else:
        player = tour.get_player(interaction.message.mentions[0].id)

    if player is None:
        await interaction.send("Something went wrong finding that player")
    else:
        if tour.phase == Phase.SIGNUP:
            tour.remove_player(player.id)
        else:
            player.dropped = True
        await interaction.send("Done", ephemeral=True)
        await interaction.channel.send(f"<@{player.id}> has been dropped from {tour.name}")


@synced_user_command(admin=True, name="Full Paste")
@command_phases(
    Phase.BETWEEN_ROUNDS, Phase.DURING_ROUND, Phase.TOP_CUT, Phase.ENDED,
    any_channel=True,
    extra_check=lambda tour: tour.require_paste
)
async def tournament_get_team_paste(tour: Tournament, interaction: UserInter, user: disnake.User):
    player = tour.get_player(user.id)
    if player is None:
        await interaction.send(f"{user.mention} doesn't seem to be in {tour.name}...", ephemeral=True)
    else:
        await interaction.send(f"{user.mention}'s full paste: {player.paste}", ephemeral=True)


@synced_user_command(name="Player Info")
@command_phases(
    Phase.BETWEEN_ROUNDS, Phase.DURING_ROUND, Phase.TOP_CUT, Phase.ENDED,
    any_channel=True,
    extra_check=lambda tour: tour.require_team_sheet
)
async def tournament_get_team_paste(tour: Tournament, interaction: UserInter, user: disnake.User):
    player = tour.get_player(user.id)
    if player is None:
        await interaction.send(f"{user.mention} doesn't seem to be in {tour.name}...", ephemeral=True)
    else:
        await interaction.send(embed=player_info_embed(tour, player, user), ephemeral=True)


@synced_slash(admin=True)
@command_phases(
    Phase.SIGNUP, Phase.BETWEEN_ROUNDS, Phase.DURING_ROUND, Phase.TOP_CUT, Phase.ENDED,
    any_channel=True,
    extra_check=lambda tour: tour.require_team_sheet
)
async def tournament_get_all_pastes(tour: Tournament, interaction: UserInter):
    """
    Prints all the team pastes for TO checking.
    """
    s = "## All pastes/team sheets:"
    for player in tour.player_dict.values():
        s += "\n\n" + f"<@{player.id}>"
        if tour.require_paste:
            s += "\n> paste: " + str(player.paste)
        if tour.require_team_sheet:
            s += "\n> team sheet: " + str(player.team_sheet)

    await interaction.send(s, ephemeral=True, allowed_mentions=disnake.AllowedMentions.none())


@synced_slash(name="opponent_info")
@command_phases(Phase.DURING_ROUND)
async def tournament_get_opponent_info(tour: Tournament, interaction: SlashInter):
    """
    Gets the info for your next opponent.
    """
    player = tour.get_player(interaction.author.id)
    if player is None:
        await interaction.send(f"You don't seem to be in {tour.name}...", ephemeral=True)
    elif player.latest_match().round_number != tour.current_round:
        await interaction.send(f"You don't have an opponent this round...", ephemeral=True)
    else:
        opponent = find(lambda p: p is not player, player.latest_match().players)
        op_user = await interaction.guild.fetch_member(opponent.id)
        await interaction.send(embed=player_info_embed(tour, opponent, op_user), ephemeral=True)


def player_info_embed(tour, player, user) -> disnake.Embed:
    embed = disnake.Embed(
        title=player.tag,
        description=f"{player.record_str()}",
        color=disnake.Color.dark_orange()
    )
    embed.set_author(
        name=user.display_name,
        icon_url=user.display_avatar.url
    )
    embed.set_footer(
        text=tour.name
    )
    if tour.require_team_sheet:
        embed.add_field(
            name="Team Sheet",
            value=player.team_sheet,
            inline=False
        )
    if tour.challenge != "":
        embed.add_field(
            name="Challenge",
            value=tour.challenge.format(tag=player.tag)
        )
    return embed


@synced_slash(admin=True)
@command_phases(Phase.BETWEEN_ROUNDS)
async def tournament_start_top_cut(
        tour: Tournament, interaction: SlashInter,
        num_players: int = Param(name="number_of_players", choices=[2, 4, 8, 16])):
    """
    Starts the top cut
    """

    await interaction.send("Working on Pairings.", ephemeral=True)

    new_matches = tour.top_cut(num_players)

    await interaction.channel.send(f"# Pairings for top {num_players}:")

    view = disnake.ui.View()
    view.add_item(report_score.button)

    for i, mp in enumerate(new_matches):
        await interaction.channel.send(
            f"{i+1}. <@{mp.players[0].id}> "
            f"vs <@{mp.players[1].id}>",
            view=view
        )

    await sync_to_phase(tour, Phase.TOP_CUT, interaction.guild)


@synced_slash(admin=True)
@command_phases(Phase.TOP_CUT)
async def tournament_next_cut(tour: Tournament, interaction: SlashInter):
    """
    Continue to the next part of the top cut.
    """
    await interaction.send("Working on Pairings.", ephemeral=True)

    new_matches = tour.next_cut()

    await interaction.channel.send(f"# Pairings for top {len(new_matches)*2}:")

    view = disnake.ui.View()
    view.add_item(report_score.button)

    for i, mp in enumerate(new_matches):
        await interaction.channel.send(
            f"{i+1}. <@{mp.players[0].id}> "
            f"vs <@{mp.players[1].id}>",
            view=view
        )

    await sync_to_phase(tour, Phase.TOP_CUT, interaction.guild)


@synced_slash(admin=True)
@command_phases(Phase.TOP_CUT, Phase.BETWEEN_ROUNDS)
async def tournament_end(tour: Tournament, interaction: SlashInter):
    """
    Ends the tournament.
    """
    await interaction.send("Working on Pairings.", ephemeral=True)

    await interaction.channel.send(f"# {tour.name} has ended!" + "\n\n" +
                                   f"## Congratulation to <@{tour.winner().id}> for winning!")

    await sync_to_phase(tour, Phase.ENDED, interaction.guild)


@synced_slash(admin=True)
@command_phases(Phase.ENDED)
async def tournament_close(tour: Tournament, interaction: SlashInter):
    """
    Deletes the tournament and removes all relevant commands from your server
    """
    Tournament.close(tour)
    await interaction.send("You have closed out the tournament.", ephemeral=True)

    for com in phased_commands:
        # noinspection PyUnresolvedReferences
        await toggle_command(interaction.guild, com, only_add_remove=False)
