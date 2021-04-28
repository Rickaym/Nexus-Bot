import time


class AntiAbuse:
    def __init__(self):
        self.watching_sessions = {}

    def start_watching_session(self, guild_id, channel_id, rounds, members):
        session_id = str(guild_id)+str(channel_id)
        self.watching_sessions[session_id] = (rounds, members, time.time())

    def flag_suspicious(self, session_id, guild_id, channel_id, flag):
        rounds, members, time_started = self.watching_sessions[session_id]
        details = f"[DETAILS]\n\nSessionID: {session_id}\nGuild: {guild_id}\nChannel: {channel_id}\n\nRounds: {rounds}\nMax, Min: {rounds*len(members)}, {rounds*-10}\nMembers: {', '.join([str(member.display_name)+'#'+str(member.discriminator) for member in members])}"
        durationS, durationM = round(time.time() - time_started), 0
        while durationS >= 60:
            durationS -= 60
            durationM += 1

        if flag[0] == "scores":
            report = '\n'.join(
                [f'{key} = {flag[1][key]}' for key in flag[1].keys()])
            suspicion = f"[SCORE UNINTEGRITY]\n\nCulprit(s): {', '.join([user for user in flag[2]])}\nReports: {report}\nTime Took: {durationM} minutes and {durationS} seconds"
        elif flag[0] == "rounds":
            suspicion = f"[ROUNDS UNINTEGRITY]\n\nRounds: {rounds}"
        elif flag[0] == "exit":
            suspicion = f"[IMPROPER EXIT]\n\nError: {flag[1]}\nTime Took: {durationM} minutes and {durationS} seconds"

        return f"[ACTIVITY FLAGGED SUSPICIOUS]|{details}|{suspicion}"

    def do_reality_check(self, scores, guild_id, channel_id):
        session_id = str(guild_id)+str(channel_id)
        rounds, members, time_started = self.watching_sessions[session_id]
        highest_possible = 7 * len(members)
        lowest_possible = -10 * rounds
        flag = False
        statistics = {}
        violators = []
        for member in members:
            if (score := int(scores[member.id])) >= highest_possible or int(scores[member.id]) <= lowest_possible:
                flag = True
                violators.append(str(member.display_name) +
                                 '#'+str(member.discriminator))
            statistics[str(member.display_name)+'#' +
                       str(member.discriminator)] = score
        if flag:
            return self.flag_suspicious(str(guild_id)+str(channel_id), guild_id, channel_id, ["scores", statistics, violators])
        return None

    def do_entrance_check(self, guild_id, channel_id):
        session_id = str(guild_id)+str(channel_id)
        rounds, members, time_started = self.watching_sessions[session_id]
        if rounds >= 5:
            return self.flag_suspicious(str(guild_id)+str(channel_id), guild_id, channel_id, ["rounds", rounds, members])
        return None

    def do_exit_check(self, guild_id, channel_id, lobbyinit_id, data):
        flag = False
        target = []  # self.channels[guild_id], self.to_ready_up[lobby_init], self.to_complete_answers[channel.id], self.scores[channel.id]]
        try:
            data[0][guild_id]
        except KeyError:
            pass
        else:
            flag = True
            target.append(data[0][guild_id])

        try:
            data[1][lobbyinit_id]
        except KeyError:
            pass
        else:
            flag = True
            target.append(data[1][lobbyinit_id])

        try:
            data[2][channel_id]
        except KeyError:
            pass
        else:
            flag = True
            target.append(data[2][channel_id])

        try:
            data[3][channel_id]
        except KeyError:
            pass
        else:
            flag = True
            target.append(data[3][channel_id])

        if flag:
            return self.flag_suspicious(str(guild_id)+str(channel_id), guild_id, channel_id, ["exit", target])

    def end_watching_session(self, guild_id, channel_id):
        session_id = str(guild_id)+str(channel_id)
        self.watching_sessions.pop(session_id)
