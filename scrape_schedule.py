import requests
from bs4 import BeautifulSoup
import json
from scrape_genres import get_game_genres
from dateutil.parser import parse
from urllib import urlencode


def get_games_list():
    req = requests.get('https://gamesdonequick.com/schedule')
    soup = BeautifulSoup(req.text)
    table = soup.find('tbody')

    first_rows = table.findAll('tr', attrs={'class': None})
    games = list()
    for row in first_rows:
        second_row = row.findNext('tr', attrs={'class': 'second-row'})
        duration = 0
        if second_row:
            duration = second_row.findNext('td').text.strip()
        runner_text = row.find('td', attrs={'rowspan': 2})
        runner = runner_text.text.strip() if runner_text else ""
        game = {
            'title': row.find('td', attrs={'class': None}).text,
            'duration': duration,
            'runner': runner
        }
        games.append(game)
    return games


def giant_bomb_search(name):
    base_url = "http://www.giantbomb.com/api/search/"
    with open('api_keys.json', 'r') as f:
        api_key = json.load(f)['giant_bomb']
    headers = {'User-agent': 'Python'}
    params = {
        'api_key': api_key,
        'format': 'json',
        'query': name.encode('ascii', 'replace'),
        'resources': 'game',
        'limit': 10
    }
    results = requests.get(base_url, headers=headers, params=params).json()
    manual_results = ['-1: **None of these results**']
    for i, res in enumerate(results['results']):
        if(res['name'] == name):
            return res
        res_name = res['name'].encode('utf-8', 'ignore')
        res_id = res['id']
        try:
            res_date = res['original_release_date']
            res_date = parse(res_date).strftime('%Y-%m-%d')
        except:
            res_date = ''
        manual_results.append("{0}: {1} ({2}) - {3}".format(i,
                                                            res_name,
                                                            res_id,
                                                            res_date))
    else:
        print "\n".join(manual_results)
        print "Title: {0}".format(name.encode('utf-8', 'ignore'))
        correct = int(input("Correct Index: "))
        if correct < 0:
            return {}
    return results['results'][correct]


def giant_bomb_game_data(game_id):
    base_url = "http://www.giantbomb.com/api/game/{}".format(game_id)
    with open('api_keys.json', 'r') as f:
        api_key = json.load(f)['giant_bomb']
    headers = {'User-agent': 'Python'}
    params = {
        'api_key': api_key,
        'format': 'json'
    }
    response = requests.get(base_url, headers=headers, params=params).text
    try:
        return json.loads(response)['results']
    except Exception:
        print response


def match_games_auto(games_list):
    for i, game in enumerate(games_list):
        if 'data' in game and game['data'] is not None:
            continue
        ascii_title = game['title'].encode('ascii', 'ignore')
        print "({0}/{1}) Searching for: {2}".format(i + 1,
                                                    len(games_list),
                                                    ascii_title)
        game['data'] = giant_bomb_search(games_list[i]['title'])
    return games_list


def match_games_manual(games_list):
    for game in games_list:
        if game['data'] == {}:
            print "Title: {0}".format(game['title'].encode('ascii', 'replace'))
            game_id = raw_input("Game ID: ")
            if game_id == "x":
                continue
            game['data'] = giant_bomb_game_data(game_id)
    return [x for x in games_list if x['data']]


def get_google_search_link(query):
    return 'https://google.com/Search?{}'.format(urlencode(dict(q=query)))


def process_game_platforms(games_list):
    num_games = len(games_list)
    for i, game in enumerate(games_list):
        if "platform" in game:
            continue
        query = game['title'] + ' game'
        print "Search Link: {}".format(get_google_search_link(query))
        game_title = game['title'].encode('ascii', 'replace')
        p = raw_input("({0}/{1}) {2}:".format(i + 1,
                                              num_games,
                                              game_title))
        games_list[i]['platform'] = p
    return games_list


def filter_blacklisted_games(games_list):
    black_list = ['Pre-Show', 'Setup Block', 'Finale']
    black_list = map(lambda x: x.lower(), black_list)
    return [x for x in games_list if not any(x['title'].lower().startswith(y)
            for y in black_list)]


def add_game_genres(games_list):
    for i, g in enumerate(games_list):
        ascii_title = g['title'].encode('ascii', 'ignore')
        print("({0}/{1}) Searching for: {2}".format(i + 1,
                                                    len(games_list),
                                                    ascii_title))
        try:
            g['data']['genres'] = get_game_genres(g['data']['id'])
        except:
            print '*** Genre scraping failed for: {}'.format(g['title'])
    return games_list

if __name__ == '__main__':
    print("*** [1/5] Getting games list from Schedule...")
    raw_games = get_games_list()
    raw_games = filter_blacklisted_games(raw_games)

    print("*** [2/5] Attempting to automatically match games to data...")
    raw_games = match_games_auto(raw_games)

    print("*** [3/5] Manually fixing game data...")
    raw_games = match_games_manual(raw_games)

    print("*** [4/5] Prompting for marathon platform...")
    raw_games = process_game_platforms(raw_games)

    print("*** [5/5] Downloading game genres...")
    raw_games = add_game_genres(raw_games)

    with open('scraped_games.json', 'w+') as f:
        json.dump(raw_games, f)
