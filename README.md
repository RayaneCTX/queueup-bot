# QueueUp Discord Bot
Basically QueueUp Live But on Discord

## Running it Locally
You would need to create environment variables in order for the program to work. 
```
TOKEN=[Token from Discord API]
QUEUE_CHANNEL_ID=[Text Channel ID to run the queue in]
HISTORY_CHANNEL_ID=[Text Channel ID to store history]
UTA_ROLE_ID=[Role ID for the UTAs]
GTA_ROLE_ID=[Role ID for the GTAs]
PROFESSOR_ROLE_ID=[Role ID for Professor] 
WAITING_ROOM=[Voice Channel ID for Waiting Room]
BOT_CHANNEL_ID=[Text Channel ID for bot commands only for TAs]
ROOMS="{'voice channel': 'text channel'}"
DATABASE=[Location of the Database]
```
For rooms, each voice channel will be assigned a text channel. As a result, if there is a video failure, the TA and student can still connect via text channel.

You can store the environment variables inside a .env file. In production, it doesn't use load_dotenv, so do not create .env for production. 

To run it, you can run bin/gueueup-bot directly. 
```bash
python3 bin/queueup-bot
```

## Installation [Production]
You can install it using the following command
```bash
python3 setup.py install --user
```

You run it using the following
```bash
queueup-bot
```

## Basic setup [Production]
```.
Home Directory
│
├─── environments 
│    └── queueup.environment [Location to store enivronment variables]
│
├─── scripts 
│    └── queueup.sh [Used only for CI/CD. It is optional]
```

