if False:
    from Deception.dummy import Member
    from Deception.ext import Local_Game_Instance,  default_ranks
    from Deception.utils import get_info

    import random

    p1 = Member("p1", random.randint(34, 1231546276236))
    p2 = Member("p2", random.randint(34, 1231546276236))
    a = Local_Game_Instance(
        0x0, [p1, p2], default_ranks, 12344)

    player = a.get_player(p1)
    abc = player.skill(player, a.get_player(p2))
    print(get_info(a.get_player(p1)).guide)
