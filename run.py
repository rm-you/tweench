from archiver import producer
from archiver import consumer

p = producer.Producer()
p.add_subreddit("awwnime")

c = consumer.Consumer()
while True:
    c.run_once()
