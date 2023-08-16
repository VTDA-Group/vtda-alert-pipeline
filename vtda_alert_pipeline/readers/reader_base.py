import abc

class Reader(abc.ABC):
    """Abstract class for stream reader."""
    
    @abc.abstractmethod
    def __init__(
        self,
        streaming_client,
        filter_list,
        database,
    ):
        self.client = streaming_client
        self.filters = filter_list
        self.database = database
        
    @abc.abstractmethod
    def query_stream(self):
        """Start processing stream.
        Should keep open connection to stream,
        and whenever a new locus comes in, should save as LightCurve object using
        _import_object, apply filters, and save to the database."""
        pass
    
    @abc.abstractmethod
    def _import_object(self, obj):
        """Import object from stream and convert to LightCurve object.
        """
        pass
        
        

