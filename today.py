import datetime
from dateutil import relativedelta
import requests
import os
from lxml import etree
import time
import hashlib
from spotify_tracker import format_current_playing

# Fine-grained personal access token with All Repositories access:
# Account permissions: read:Followers, read:Starring, read:Watching
# Repository permissions: read:Commit statuses, read:Contents, read:Issues, read:Metadata, read:Pull Requests
# Issues and pull requests permissions not needed at the moment, but may be used in the future
HEADERS = {'authorization': 'token '+ os.environ['ACCESS_TOKEN']}
USER_NAME = os.environ['USER_NAME'] # 'mxxnpy'
QUERY_COUNT = {'user_getter': 0, 'follower_getter': 0, 'graph_repos_stars': 0, 'recursive_loc': 0, 'graph_commits': 0, 'loc_query': 0}


def daily_readme(birthday):
    """
    Returns the length of time since I was born
    e.g. 'XX years, XX months, XX days'
    """
    print("[DEBUG] Calculating age...")
    diff = relativedelta.relativedelta(datetime.datetime.today(), birthday)
    result = '{} {}, {} {}, {} {}{}'.format(
        diff.years, 'year' + format_plural(diff.years), 
        diff.months, 'month' + format_plural(diff.months), 
        diff.days, 'day' + format_plural(diff.days),
        ' 🎂' if (diff.months == 0 and diff.days == 0) else '')
    print(f"[DEBUG] Age result: {result}")
    return result


def countdays(target_date):
    print("[DEBUG] Calculating countdown...")
    today = datetime.datetime.today()
    diff = target_date - today
    days_remaining = diff.days
    
    if days_remaining > 0:
        result = f"{days_remaining} days remaining"
    elif days_remaining == 0:
        result = "Today!"
    else:
        result = f"{abs(days_remaining)} days ago"
    
    print(f"[DEBUG] Countdown result: {result}")
    return result


def format_plural(unit):
    """
    Returns a properly formatted number
    e.g.
    'day' + format_plural(diff.days) == 5
    >>> '5 days'
    'day' + format_plural(diff.days) == 1
    >>> '1 day'
    """
    return 's' if unit != 1 else ''


def simple_request(func_name, query, variables):
    """
    Returns a request, or raises an Exception if the response does not succeed.
    """
    request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables':variables}, headers=HEADERS)
    if request.status_code == 200:
        return request
    raise Exception(func_name, ' has failed with a', request.status_code, request.text, QUERY_COUNT)


def graph_commits(start_date, end_date):
    """
    Uses GitHub's GraphQL v4 API to return my total commit count
    """
    query_count('graph_commits')
    query = '''
    query($start_date: DateTime!, $end_date: DateTime!, $login: String!) {
        user(login: $login) {
            contributionsCollection(from: $start_date, to: $end_date) {
                contributionCalendar {
                    totalContributions
                }
            }
        }
    }'''
    variables = {'start_date': start_date,'end_date': end_date, 'login': USER_NAME}
    request = simple_request(graph_commits.__name__, query, variables)
    return int(request.json()['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions'])


def graph_repos_stars(count_type, owner_affiliation, cursor=None, add_loc=0, del_loc=0):
    """
    Uses GitHub's GraphQL v4 API to return my total repository, star, or lines of code count.
    """
    print(f"[DEBUG] Getting {count_type} data...")
    query_count('graph_repos_stars')
    query = '''
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation) {
                totalCount
                edges {
                    node {
                        ... on Repository {
                            nameWithOwner
                            stargazers {
                                totalCount
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }'''
    variables = {'owner_affiliation': owner_affiliation, 'login': USER_NAME, 'cursor': cursor}
    request = simple_request(graph_repos_stars.__name__, query, variables)
    if request.status_code == 200:
        if count_type == 'repos':
            result = request.json()['data']['user']['repositories']['totalCount']
            print(f"[DEBUG] {count_type} result: {result}")
            return result
        elif count_type == 'stars':
            result = stars_counter(request.json()['data']['user']['repositories']['edges'])
            print(f"[DEBUG] {count_type} result: {result}")
            return result


def recursive_loc(owner, repo_name, data, cache_comment, addition_total=0, deletion_total=0, my_commits=0, cursor=None):
    """
    Uses GitHub's GraphQL v4 API and cursor pagination to fetch 100 commits from a repository at a time
    Implementação iterativa para evitar RecursionError
    """
    max_iterations = 1000  # Limite de segurança
    iteration_count = 0
    
    while iteration_count < max_iterations:
        iteration_count += 1
        query_count('recursive_loc')
        
        query = '''
        query ($repo_name: String!, $owner: String!, $cursor: String) {
            repository(name: $repo_name, owner: $owner) {
                defaultBranchRef {
                    target {
                        ... on Commit {
                            history(first: 100, after: $cursor) {
                                edges {
                                    node {
                                        ... on Commit {
                                            author {
                                                user {
                                                    id
                                                }
                                            }
                                            additions
                                            deletions
                                        }
                                    }
                                }
                                pageInfo {
                                    endCursor
                                    hasNextPage
                                }
                            }
                        }
                    }
                }
            }
        }'''
        
        variables = {'repo_name': repo_name, 'owner': owner, 'cursor': cursor}
        
        try:
            request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables':variables}, headers=HEADERS, timeout=30)
            
            if request.status_code != 200:
                force_close_file(data, cache_comment)
                if request.status_code == 403:
                    raise Exception('Too many requests in a short amount of time!\nYou\'ve hit the non-documented anti-abuse limit!')
                raise Exception('recursive_loc() has failed with a', request.status_code, request.text, QUERY_COUNT)
            
            repo_data = request.json()['data']['repository']
            if repo_data['defaultBranchRef'] is None:
                return addition_total, deletion_total, my_commits
            
            history = repo_data['defaultBranchRef']['target']['history']
            
            # Processar commits desta página
            for node in history['edges']:
                if node['node']['author']['user'] == OWNER_ID:
                    my_commits += 1
                    addition_total += node['node']['additions']
                    deletion_total += node['node']['deletions']
            
            # Verificar se há mais páginas
            if not history['pageInfo']['hasNextPage'] or len(history['edges']) == 0:
                break
                
            cursor = history['pageInfo']['endCursor']
            
        except Exception as e:
            print(f"[ERROR] Exception in recursive_loc for {owner}/{repo_name} at iteration {iteration_count}: {e}")
            force_close_file(data, cache_comment)
            break
    
    if iteration_count >= max_iterations:
        print(f"[WARNING] Maximum iterations reached for {owner}/{repo_name}, stopping at {iteration_count} iterations")
    
    return addition_total, deletion_total, my_commits


def loc_query(owner_affiliation, comment_size=0, force_cache=False):
    """
    Uses GitHub's GraphQL v4 API to query all the repositories I have access to (with respect to owner_affiliation)
    Queries 60 repos at a time, because larger queries give a 502 timeout error and smaller queries send too many
    requests and also give a 502 error.
    Returns the total number of lines of code in all repositories
    """
    all_edges = []
    cursor = None
    max_iterations = 100
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        query_count('loc_query')
        query = '''
        query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
            user(login: $login) {
                repositories(first: 60, after: $cursor, ownerAffiliations: $owner_affiliation) {
                edges {
                    node {
                        ... on Repository {
                            nameWithOwner
                            defaultBranchRef {
                                target {
                                    ... on Commit {
                                        history {
                                            totalCount
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }'''
        variables = {'owner_affiliation': owner_affiliation, 'login': USER_NAME, 'cursor': cursor}
        request = simple_request(loc_query.__name__, query, variables)
        
        response_data = request.json()
        if 'data' not in response_data or not response_data['data']:
            print(f"[ERROR] Invalid API response: {response_data}")
            break
            
        repo_data = response_data['data']['user']['repositories']
        all_edges += repo_data['edges']
        
        if not repo_data['pageInfo']['hasNextPage']:
            break
            
        cursor = repo_data['pageInfo']['endCursor']
    
    return cache_builder(all_edges, comment_size, force_cache)


def cache_builder(edges, comment_size, force_cache, loc_add=0, loc_del=0):
    """
    Checks each repository in edges to see if it has been updated since the last time it was cached
    If it has, run recursive_loc on that repository to update the LOC count
    """
    cached = True # Assume all repositories are cached
    filename = 'cache/'+hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest()+'.txt' # Create a unique filename for each user
    try:
        with open(filename, 'r') as f:
            data = f.readlines()
    except FileNotFoundError: # If the cache file doesn't exist, create it
        data = []
        if comment_size > 0:
            for _ in range(comment_size): data.append('This line is a comment block. Write whatever you want here.\n')
        with open(filename, 'w') as f:
            f.writelines(data)

    if len(data)-comment_size != len(edges) or force_cache: # If the number of repos has changed, or force_cache is True
        cached = False
        flush_cache(edges, filename, comment_size)
        with open(filename, 'r') as f:
            data = f.readlines()

    cache_comment = data[:comment_size] # save the comment block
    data = data[comment_size:] # remove those lines
    for index in range(len(edges)):
        repo_hash, commit_count, *__ = data[index].split()
        if repo_hash == hashlib.sha256(edges[index]['node']['nameWithOwner'].encode('utf-8')).hexdigest():
            try:
                if int(commit_count) != edges[index]['node']['defaultBranchRef']['target']['history']['totalCount']:
                    # if commit count has changed, update loc for that repo
                    owner, repo_name = edges[index]['node']['nameWithOwner'].split('/')
                    loc = recursive_loc(owner, repo_name, data, cache_comment)
                    data[index] = repo_hash + ' ' + str(edges[index]['node']['defaultBranchRef']['target']['history']['totalCount']) + ' ' + str(loc[2]) + ' ' + str(loc[0]) + ' ' + str(loc[1]) + '\n'
            except TypeError: # If the repo is empty
                data[index] = repo_hash + ' 0 0 0 0\n'
    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)
    for line in data:
        loc = line.split()
        loc_add += int(loc[3])
        loc_del += int(loc[4])
    return [loc_add, loc_del, loc_add - loc_del, cached]


def flush_cache(edges, filename, comment_size):
    """
    Wipes the cache file
    This is called when the number of repositories changes or when the file is first created
    """
    with open(filename, 'r') as f:
        data = []
        if comment_size > 0:
            data = f.readlines()[:comment_size] # only save the comment
    with open(filename, 'w') as f:
        f.writelines(data)
        for node in edges:
            f.write(hashlib.sha256(node['node']['nameWithOwner'].encode('utf-8')).hexdigest() + ' 0 0 0 0\n')


def add_archive():
    """
    Several repositories I have contributed to have since been deleted.
    This function adds them using their last known data
    """
    with open('cache/repository_archive.txt', 'r') as f:
        data = f.readlines()
    old_data = data
    data = data[7:len(data)-3] # remove the comment block    
    added_loc, deleted_loc, added_commits = 0, 0, 0
    contributed_repos = len(data)
    for line in data:
        repo_hash, total_commits, my_commits, *loc = line.split()
        added_loc += int(loc[0])
        deleted_loc += int(loc[1])
        if (my_commits.isdigit()): added_commits += int(my_commits)
    added_commits += int(old_data[-1].split()[4][:-1])
    return [added_loc, deleted_loc, added_loc - deleted_loc, added_commits, contributed_repos]

def force_close_file(data, cache_comment):
    """
    Forces the file to close, preserving whatever data was written to it
    This is needed because if this function is called, the program would've crashed before the file is properly saved and closed
    """
    filename = 'cache/'+hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest()+'.txt'
    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)
    print('There was an error while writing to the cache file. The file,', filename, 'has had the partial data saved and closed.')


def stars_counter(data):
    """
    Count total stars in repositories owned by me
    """
    total_stars = 0
    for node in data: total_stars += node['node']['stargazers']['totalCount']
    return total_stars


def svg_overwrite(filename, age_data, commit_data, star_data, repo_data, contrib_data, follower_data, loc_data, countdown_data, spotify_data):
    """
    Parse SVG files and update elements with my age, commits, stars, repositories, and lines written
    """
    print(f"[DEBUG] Updating SVG: {filename}")
    tree = etree.parse(filename)
    root = tree.getroot()
    justify_format(root, 'age_data', age_data)
    justify_format(root, 'countdown_data', countdown_data)
    justify_format(root, 'commit_data', commit_data, 22)
    justify_format(root, 'repo_data', repo_data, 6)
    justify_format(root, 'contrib_data', contrib_data)
    justify_format(root, 'loc_data', loc_data[2], 9)
    justify_format(root, 'loc_add', loc_data[0])
    justify_format(root, 'loc_del', loc_data[1], 7)
    spotify_display = f"{spotify_data.get('track', 'Nothing')} - {spotify_data.get('artist', 'Nobody')}"
    justify_format(root, 'spotify_track', spotify_display)
    tree.write(filename, encoding='utf-8', xml_declaration=True)
    print(f"[DEBUG] SVG {filename} updated successfully")


def justify_format(root, element_id, new_text, length=0):
    """
    Updates and formats the text of the element, and modifes the amount of dots in the previous element to justify the new text on the svg
    """
    if isinstance(new_text, int):
        new_text = f"{'{:,}'.format(new_text)}"
    new_text = str(new_text)
    find_and_replace(root, element_id, new_text)
    just_len = max(0, length - len(new_text))
    if just_len <= 2:
        dot_map = {0: '', 1: ' ', 2: '. '}
        dot_string = dot_map[just_len]
    else:
        dot_string = ' ' + ('.' * just_len) + ' '
    find_and_replace(root, f"{element_id}_dots", dot_string)


def find_and_replace(root, element_id, new_text):
    """
    Finds the element in the SVG file and replaces its text with a new value
    """
    element = root.find(f".//*[@id='{element_id}']")
    if element is not None:
        element.text = new_text


def commit_counter(comment_size):
    """
    Counts up my total commits, using the cache file created by cache_builder.
    """
    total_commits = 0
    filename = 'cache/'+hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest()+'.txt' # Use the same filename as cache_builder
    with open(filename, 'r') as f:
        data = f.readlines()
    cache_comment = data[:comment_size] # save the comment block
    data = data[comment_size:] # remove those lines
    for line in data:
        total_commits += int(line.split()[2])
    return total_commits


def user_getter(username):
    """
    Returns the account ID and creation time of the user
    """
    print(f"[DEBUG] Getting user data for: {username}")
    query_count('user_getter')
    query = '''
    query($login: String!){
        user(login: $login) {
            id
            createdAt
        }
    }'''
    variables = {'login': username}
    request = simple_request(user_getter.__name__, query, variables)
    user_id = request.json()['data']['user']['id']
    created_at = request.json()['data']['user']['createdAt']
    print(f"[DEBUG] User ID: {user_id}")
    return {'id': user_id}, created_at

def follower_getter(username):
    """
    Returns the number of followers of the user
    """
    print(f"[DEBUG] Getting followers for: {username}")
    query_count('follower_getter')
    query = '''
    query($login: String!){
        user(login: $login) {
            followers {
                totalCount
            }
        }
    }'''
    request = simple_request(follower_getter.__name__, query, {'login': username})
    followers = int(request.json()['data']['user']['followers']['totalCount'])
    print(f"[DEBUG] Followers: {followers}")
    return followers


def query_count(funct_id):
    """
    Counts how many times the GitHub GraphQL API is called
    """
    global QUERY_COUNT
    QUERY_COUNT[funct_id] += 1


def perf_counter(funct, *args):
    """
    Calculates the time it takes for a function to run
    Returns the function result and the time differential
    """
    start = time.perf_counter()
    funct_return = funct(*args)
    return funct_return, time.perf_counter() - start


def formatter(query_type, difference, funct_return=False, whitespace=0):
    """
    Prints a formatted time differential
    Returns formatted result if whitespace is specified, otherwise returns raw result
    """
    print('{:<23}'.format('   ' + query_type + ':'), sep='', end='')
    print('{:>12}'.format('%.4f' % difference + ' s ')) if difference > 1 else print('{:>12}'.format('%.4f' % (difference * 1000) + ' ms'))
    if whitespace:
        return f"{'{:,}'.format(funct_return): <{whitespace}}"
    return funct_return


if __name__ == '__main__':
    try:
        print('Calculation times:')
        # define global variable for owner ID and calculate user's creation date
        # e.g {'id': 'MDQ6VXNlcjU3MzMxMTM0'} and 2019-11-03T21:15:07Z for username 'Andrew6rant'
        user_data, user_time = perf_counter(user_getter, USER_NAME)
        OWNER_ID, acc_date = user_data
        formatter('account data', user_time)
        # CONFIGURAR: Sua data de nascimento (ano, mês, dia)
        age_data, age_time = perf_counter(daily_readme, datetime.datetime(2002, 4, 23))
        formatter('age calculation', age_time)
        # CONFIGURAR: Data alvo para contagem regressiva (ano, mês, dia)
        countdown_data, countdown_time = perf_counter(countdays, datetime.datetime(2026, 6, 10))
        formatter('countdown to target', countdown_time)
        try:
            total_loc, loc_time = perf_counter(loc_query, ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER'], 7)
            formatter('LOC (cached)', loc_time) if total_loc[-1] else formatter('LOC (no cache)', loc_time)
        except Exception as e:
            print(f"[WARNING] LOC query failed: {e}")
            total_loc, loc_time = [0, 0, 0, False], 0
            
        try:
            commit_data, commit_time = perf_counter(commit_counter, 7)
        except Exception as e:
            print(f"[WARNING] Commit counter failed: {e}")
            commit_data, commit_time = 0, 0
            
        try:
            repo_data, repo_time = perf_counter(graph_repos_stars, 'repos', ['OWNER'])
            contrib_data, contrib_time = perf_counter(graph_repos_stars, 'repos', ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER'])
        except Exception as e:
            print(f"[WARNING] Repository data failed: {e}")
            repo_data, repo_time = 0, 0
            contrib_data, contrib_time = 0, 0
        
        try:
            spotify_data, spotify_time = perf_counter(format_current_playing)
        except Exception as e:
            print(f"[WARNING] Spotify data failed: {e}")
            spotify_data, spotify_time = {'track': 'Error', 'artist': 'Error'}, 0

        # several repositories that I've contributed to have since been deleted.
        # CONFIGURAR: Substitua pelo seu ID do GitHub ou remova esta seção
        if OWNER_ID == {'id': 'U_kgDOCgekhQ'}: # only calculate for user mxxnpy
            archived_data = add_archive()
            for index in range(len(total_loc)-1):
                total_loc[index] += archived_data[index]
            contrib_data += archived_data[-1]
            commit_data += int(archived_data[-2])

        for index in range(len(total_loc)-1): total_loc[index] = '{:,}'.format(total_loc[index]) # format added, deleted, and total LOC

        svg_overwrite('dark_mode.svg', age_data, commit_data, None, repo_data, contrib_data, None, total_loc[:-1], countdown_data, spotify_data)
        svg_overwrite('light_mode.svg', age_data, commit_data, None, repo_data, contrib_data, None, total_loc[:-1], countdown_data, spotify_data)

        # move cursor to override 'Calculation times:' with 'Total function time:' and the total function time, then move cursor back
        print('\033[F\033[F\033[F\033[F\033[F\033[F\033[F\033[F',
            '{:<21}'.format('Total function time:'), '{:>11}'.format('%.4f' % (user_time + age_time + countdown_time + loc_time + commit_time + repo_time + contrib_time + spotify_time)),
            ' s \033[E\033[E\033[E\033[E\033[E\033[E\033[E\033[E', sep='')

        print('\n=== RESULTS ===')
        print(f'Age: {age_data}')
        print(f'Countdown: {countdown_data}')
        print(f'Total commits: {commit_data:,}')
        print(f'Repositories owned: {repo_data:,}')
        print(f'Repositories contributed: {contrib_data:,}')
        print(f'Lines added: {total_loc[0]}')
        print(f'Lines deleted: {total_loc[1]}')
        print(f'Total lines of code: {total_loc[2]}')
        print(f'Spotify: {spotify_data.get("track", "Nothing")} - {spotify_data.get("artist", "Nobody")}')

        print('\nTotal GitHub GraphQL API calls:', '{:>3}'.format(sum(QUERY_COUNT.values())))
        for funct_name, count in QUERY_COUNT.items(): print('{:<28}'.format('   ' + funct_name + ':'), '{:>6}'.format(count))
        
    except Exception as e:
        print(f"[CRITICAL ERROR] Script failed: {e}")
        print("Attempting to continue with partial data...")
        import traceback
        traceback.print_exc()