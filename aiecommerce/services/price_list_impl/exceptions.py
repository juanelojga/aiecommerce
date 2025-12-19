class IngestionError(Exception):
    pass


class UrlResolutionError(IngestionError):
    pass


class DownloadError(IngestionError):
    pass


class ParsingError(IngestionError):
    pass
