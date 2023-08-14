import numpy as np
import matplotlib.pyplot as plt
from alerce.core import Alerce
from datetime import date
from astropy.time import Time


alerce = Alerce()


today = Time(str(date.today())+'T00:00:00').mjd


# Query Alerce...
dataframe = alerce.query_objects(
    classifier="stamp_classifier",
    class_name="SN",
    format="pandas",
    lastmjd = today - 7,
    firstmjd = today - 100,
    page_size = 10,
    probability = 0.8
)

for index, sn_candidate in dataframe.iterrows():
	detections = alerce.query_detections(sn_candidate['oid'],
                                     format="pandas")
	print(detections)
	print(detections.keys())
	plt.errorbar(detections['mjd'], detections['magpsf'],yerr=detections['sigmapsf'])
	plt.show()




sys.exit()
