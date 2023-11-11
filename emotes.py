from enum import StrEnum
import random


class Emotes(StrEnum):
    TANGELA = "<:tangela_shoes:1008434764417617920>"
    FALINKS_MARCH = "<a:falinks:887379443822252082>"
    CHARGA_PET = "<a:charga_pet:1125849966896762950>"
    GOODRA = "<:goodra_confusion:1008434750328930484>"
    EGGY = "<:eggytroll:1008434767659794532>"
    HAX = "<:happy_hax:1008436004115456000>"
    HAWLUCHA = "<:hawlucha_thumpsup:1008434739969007726>"
    MAROWAK = "<:marowak_coolguy:1008434753806016652>"
    PORY = "<:poryY:1011496058620235900>"
    SALAZZLE = "<:salazzle_smile:1008434752228962344>"
    SLOWPOKE = "<:slowpoke_waawaa:1008434747044798564>"
    SNORLAX = "<:snorlax_eatsleep_english:1008434745014763550>"
    TORKOAL = "<:torkoal_angry:1008434741596397690>"
    WHIMS = "<:whimsicott_charm:1008434748756070530>"
    GYARADOS = ("<:gyarados_scary:1008434755378884658><:gyarados_watergun1:1008434756842704906><:gyarados_watergun2"
                ":1008434758818205886>")

    @staticmethod
    def random_spam():
        i = random.random()
        if i < .33:
            return Emotes.TANGELA + Emotes.TANGELA
        elif i < .66:
            j = random.randint(1, 1048576)
            s = str(Emotes.CHARGA_PET)
            while j < 1048576:
                s += Emotes.CHARGA_PET
                j = j * 2
            return s
        elif i < .95:
            return random.choice([Emotes.FALINKS_MARCH, Emotes.GOODRA, Emotes.EGGY, Emotes.HAX, Emotes.SNORLAX,
                                  Emotes.HAWLUCHA, Emotes.MAROWAK, Emotes.PORY, Emotes.SALAZZLE, Emotes.SLOWPOKE,
                                  Emotes.TORKOAL, Emotes.WHIMS])
        else:
            return Emotes.GYARADOS + random.choice([Emotes.GOODRA, Emotes.EGGY, Emotes.SLOWPOKE])

