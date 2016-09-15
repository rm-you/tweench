from archiver import consumer

c = consumer.Consumer()
while True:
    c.run_once()
