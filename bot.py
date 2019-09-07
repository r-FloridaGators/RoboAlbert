from config import CLIENT_ID, CLIENT_SECRET, PASSWORD
import datetime
import schedule
import requests
import praw
import time
import sys


if '--test' in sys.argv:
    target_sub = 'FloridaGatorsDev'
else:
    target_sub = 'FloridaGators'


r = praw.Reddit(client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                password=PASSWORD,
                user_agent='RoboAlbert v0.3',
                username='RoboAlbert')


game_thread_title = '[Game Thread] Florida {home_away} {opponent_school} ({start_time}, {broadcast})'

football_thread_body = """
## Florida Gators {home_away} {opponent_school} {opponent_name}

| Team | 1st | 2nd | 3rd | 4th | Total|
|-----:|:---:|:---:|:---:|:---:|:----:|
|Florida|{t0_q1}|{t0_q2}|{t0_q3}|{t0_q4}|{t0_total}|
|{opponent_school}|{t1_q1}|{t1_q2}|{t1_q3}|{t1_q4}|{t1_total}|

---

| TIME | TV | STREAMS | SPREAD | O/U |
|:----:|:--:|:-------:|:------:|:---:|
|{start_time}|{broadcast}|VIDEO AUDIO|{spread}|{over_under}|
"""


def check_football():
    scores = requests.get('http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard').json()
    for i in scores['events']:
        if 'Florida Gators' in i['name']:
            game_id = i['id']
            event = requests.get('http://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={}'.format(game_id)).json()
            broadcast = event['header']['competitions'][0]['broadcasts'][0]['media']['shortName']
            spread = event['pickcenter'][0]['spread']
            over_under = event['pickcenter'][0]['overUnder']
            opponent_school = event['boxscore']['teams'][0]['team']['location']
            opponent_name = event['boxscore']['teams'][0]['team']['name']
            start_date, start_time = (i.strip() for i in event['header']['competitions'][0]['status']['type']['shortDetail'].split('-'))
            # determine neutral or home/away
            if event['header']['competitions'][0]['neutralSite']:
                home_away = 'vs'
            else:
                for i in event['header']['competitions'][0]['competitors']:
                    if i['team']['location'] == 'Florida':
                        if i['homeAway'] == 'home':
                            home_away = 'vs'
                        else:
                            home_away = 'at'

            # complete garbage but works on windows + linux
            today_date = '/'.join([str(int(i)) for i in datetime.datetime.now().strftime('%m/%d').split('/')])
            
            thread_title = game_thread_title.format(
                home_away = home_away,
                opponent_school = opponent_school,
                start_time = start_time,
                broadcast = broadcast
            )

            thread_body = football_thread_body.format(
                home_away = home_away,
                opponent_school = opponent_school,
                opponent_name = opponent_name,
                t0_q1 = 0,
                t0_q2 = 0,
                t0_q3 = 0,
                t0_q4 = 0,
                t0_total = 0,
                t1_q1 = 0,
                t1_q2 = 0,
                t1_q3 = 0,
                t1_q4 = 0,
                t1_total = 0,
                start_time = start_time,
                broadcast = broadcast,
                spread = spread,
                over_under = over_under
            )

            hour, minute = start_time.split(':')
            hour = int(hour)
            minute = int(minute.split()[0])

            if hour > 10:
                thread_start = str(hour - 1) + ':' + str(minute).zfill(2)
            else:
                thread_start = str(hour - 1 + 12) + ':' + str(minute).zfill(2)

            if today_date == start_date:
                print('Scheduling game thread for ' + thread_start)
                schedule.every().day.at(thread_start).do(post_thread, 
                                                         title=thread_title,
                                                         body=thread_body,
                                                         game_thread=True)


def post_thread(title='', body='', sub=target_sub, game_thread=False):
    try:
        r.subreddit(sub).submit(title, selftext=body)
        print('Successfully posted {}'.format(title))

    except Exception as e:
        print('Failed to post {}: {}'.format(title, e))

    if game_thread:
        return schedule.CancelJob


def thread_monitor():
    for submission in r.subreddit(target_sub).new(limit=25):
        post_date = datetime.datetime.fromtimestamp(submission.created_utc)
        post_age = datetime.datetime.now() - post_date

        # Sticky new RoboAlbert Threads
        if submission.author == 'RoboAlbert':
            if post_age.days < 1:
                # sort the comments
                submission.mod.suggested_sort(sort='new')
                if not submission.stickied:
                    # Sticky the post
                    submission.mod.sticky(state=True)
            else:
                if submission.stickied:
                    # remove old sticky
                    submission.mod.sticky(state=False)

        # New threads set to contest mode
        if post_age.total_seconds() < 7200:
            if post_age.total_seconds() < 3600:
                submission.mod.contest_mode(state=True)
            else:
                submission.mod.contest_mode(state=False)


if __name__ == '__main__':
    # TODO
    #schedule.every().sunday.at('06:00').do(sunday_qb)
    #schedule.every().sunday.at('06:00').do(weekly_update)

    # Automoderate
    schedule.every(30).seconds.do(thread_monitor)

    # Game Threads
    schedule.every().day.at('06:00').do(check_football)

    # Weekly Threads
    schedule.every().monday.at('06:00').do(post_thread, title='Monday Moan Thread')
    schedule.every().wednesday.at('06:00').do(post_thread, title='Whatever Wednesday Thread')
    schedule.every().wednesday.at('06:00').do(post_thread, title='Weekly Prediction Thread', body='Make your predictions for the games this weekend')
    schedule.every().thursday.at('06:00').do(post_thread, title='r/FloridaGators Pick\'em Reminder', body='GET YOUR PICKS LOCKED IN')
    schedule.every().thursday.at('06:00').do(post_thread, title='TRASH TALK THURSDAY', body='SMASH THAT CAPS LOT AND TALK SOME TRASH')
    schedule.every().friday.at('07:00').do(post_thread, title='Free Talk Friday')


    try:
        print('Starting RoboAlbert...')

        # forever and ever <3
        while True:
            schedule.run_pending()
            time.sleep(5)

    except (KeyboardInterrupt, SystemExit):
        print('Clearing schedule')
        schedule.clear()
        exit()
    
    except Exception as e:
        print(e)