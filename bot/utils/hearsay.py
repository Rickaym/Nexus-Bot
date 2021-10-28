

class Hearsay:
    @staticmethod
    def resolve_name(user):
        if user.name+user.discriminator == "Neo1844":
            return "**Neo** <:dev:903040958109737022>"
        else:
            return f"{user.name}#{user.discriminator}"
