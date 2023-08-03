#! /bin/sh

cd /bigmodel-finetune
gunicorn -c gunicorn.config.py app.run:app --daemon

while [ ! -f "instance/db.sqlite" ]; do
    sleep 3
    echo "bigmodel finetune service initializing..."
done

mv /bigmodel-finetune/conf/db.sqlite instance/db.sqlite
echo "bigmodel finetune service starts successfully!"
# keep container running forever 
tail -f /dev/null
