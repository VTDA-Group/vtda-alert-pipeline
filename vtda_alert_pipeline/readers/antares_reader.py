from antares_client import StreamingClient
import pandas as pd

from vtda_alert_pipeline.reader_base import Reader
from vtda_alert_pipeline.lightcurve import LightCurve


class ANTARESReader(Reader):
    
    def __init__(
        self,
        topics,
        filter_list,
        database,
    ):
        client = StreamingClient(topics)
        super().__init__(
            client,
            filter_list,
            database,
        )

        
    def query_stream(self):
        """Start processing stream."""
        try:
            for topic, locus in self.client.iter():
                lc = self._import_object(locus)
                self.filters.apply_all_filters(lc)
                self.database.add_lc(lc, properties)
        finally:
            self.client.close()
    
    
    def _import_object(self, locus_obj):
        """Import object from stream and convert to LightCurve object.
        """
        ID = locus_obj.locus_id
        
        ts_df = locus_obj.timeseries[['ant_mjd','ant_mag','ant_magerr', 'ant_passband', 'ant_ra', 'ant_dec', 'ant_survey', 'ztf_magzpsci']]
        
        upper_limit = (ts_df['ant_survey'] == 2)

        ts_df.rename(
            columns={
                "ant_mjd": "mjd",
                "ant_mag": "magnitude",
                "ztf_sigmapsf": "mag_error",
                "ztf_fid": "band",
                "ant_ra": "ra",
                "ant_dec": "dec",
                "ztf_magzpsci": "zeropoint",
            },
            in_place=True
        )


        ts_df['ID'] = np.arange(len(ts_df)).as_type(str)
        ts_df['upper_limit'] = upper_limit
        ts_df[ts_df['upper_limit']]['magnitude'] = locus_obj.alerts.properties['ant_maglim']
        
        return LightCurve(ID = ID, alerts = ts_df)
        