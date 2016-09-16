from archiver import consumer

c = consumer.Consumer()
while True:
    try:
        c.run_once()
    except Exception as e:
        print(e)
