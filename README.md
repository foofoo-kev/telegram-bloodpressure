# telegram-bloodpressure

I pretty simple telegram bot to monitor your bloodpressure

Written in python, running in docker

## Setup

### Telegram Bot

Create a new Telegram bot and copy the AccessToken.

Optional: Use the following predefined commands (under "Edit Bot -> "Edit Commands"):

```
newmeasurement - New Entry
export - Export all data as csv file
showmeasurements - show the last 10 entries
```

### Docker Setup

**1) Clone the repository**
```
git clone https://github.com/foofoo-kev/telegram-bloodpressure.git
cd telegram-bloodpressure
```

**2) Enter Telegram Token**
Edit the ```TELEGRAMBOT_TOKEN``` line in the ```docker-compose.yml```

**3) Start the bot**
```
docker-compose up -d --build
```