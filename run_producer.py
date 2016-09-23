from archiver import constants
from archiver import producer

p = producer.Producer()
p.add_subreddit("foodporn", constants.QUERY_HOT, 2)
