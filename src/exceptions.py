class TokenNotProvideError(Exception):
    ...


class TokenInvalidError(Exception):
    ...


class TokenExpireError(Exception):
    ...


class PermissionDenyError(Exception):
    ...


class NotFoundError(Exception):
    ...


class ExistError(Exception):
    ...
