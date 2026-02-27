class FcliError(Exception):
    """Base exception for FCLI"""

    pass


class SourceError(FcliError):
    """Data source error"""

    pass


class SourceUnavailableError(SourceError):
    """Source unavailable"""

    pass


class AllSourcesFailedError(SourceError):
    """All sources failed"""

    pass


class DatabaseError(FcliError):
    """Database error"""

    pass


class CacheError(FcliError):
    """Cache error"""

    pass


class ValidationError(FcliError):
    """Validation error"""

    pass


class AssetNotFoundError(FcliError):
    """Asset not found"""

    pass


class SearchError(FcliError):
    """Search error"""

    pass
