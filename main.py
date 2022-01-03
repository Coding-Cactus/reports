import repltalk, os, asyncio, flask, datetime, time, threading

client = repltalk.Client()
app = flask.Flask(__name__)

client.sid = os.getenv("sid")


async def _get_comment(self, id):
		return await self.perform_graphql(
			'comment',
			repltalk.Queries.get_comment,
			id=id
		)

repltalk.Client._get_comment = _get_comment

def plural(num):
	num = round(float(num))
	if num == 1:
		return ''
	return 's'

def get_content(report, post):
	if report.type == 'post':
		return post.title
	return post.content

def get_timediff(report):
	try:
		string = report.timestamp
		element = datetime.datetime.strptime(string,'%Y-%m-%dT%H:%M:%S.%fZ')  
		timestamp = datetime.datetime.timestamp(element)
		timediff = time.time() - timestamp
		if timediff < 60:
			return str(round(timediff)) + ' second' + plural(timediff)
		elif timediff < 3600:
			return str(round(timediff/60)) + ' minute' + plural(timediff/60)
		elif timediff < 3600 * 24:
			return str(round(timediff/3600)) + ' hour' + plural(timediff/3600)
		elif timediff < 3600 * 24 * 30.42:
			return str(round(timediff/(3600 * 24))) + ' day' + plural(timediff/(3600 * 24))
		elif timediff < 3600 * 24 * 365.25:
			return str(round(timediff/(3600 * 24 * 30.42))) + ' month' + plural(timediff/(3600 * 24 * 30.42))
		else:
			return str(round(timediff/(3600 * 24 * 365.25))) + ' year' + plural(timediff/(3600 * 24 * 365.25))
	except AttributeError:
		return None


unresolved = {}

def refresh(sec):
	def func_wrapper():
		refresh(sec)
		asyncio.run(refresh_reports())
	t = threading.Timer(sec, func_wrapper)
	t.start()
	return t

async def refresh_reports():
	global unresolved, stop_loop
	stop_loop = False
	newUnresolved = {}
	try:
		reports = await client.get_reports(resolved=False)
		async for report in reports:
			post = await report.get_attached()
			deleted = False
			try:
				post.content
				report.type
			except:
				deleted = True
			if not deleted:
				postID = str(post.id)
				if postID not in newUnresolved:
					newUnresolved[postID] = {
						'type': report.type,
						'content': get_content(report, post),
						'url': post.url,
						'reports':0,
						'reporters': {},
						'reportIDs':[],
					}
			else:
				postID = 'deleted'
				if 'deleted' not in newUnresolved:
					newUnresolved['deleted'] = {
						'reporters': {},
						'reports':0,
						'reportIDs': []
					}
			info = {
				'reportID': report.id,
				'reason': report.reason,
				'timediff': get_timediff(report),
				'report': report
			}
			if postID != "deleted":
				newUnresolved[postID]['reporters'][str(report.creator.name)] = info
			else:
				info['creator'] = str(report.creator.name)
				newUnresolved[postID]['reporters'][str(report.id)] = info
			for post in newUnresolved:
				count = 0
				lst = ''
				for reporter in newUnresolved[post]['reporters']:
					count += 1
					if post != 'deleted':
						lst += ',' + str(newUnresolved[post]['reporters'][reporter]['reportID'])
					else:
						lst += ',' + reporter						
				newUnresolved[post]['reports'] = count
				newUnresolved[post]['reportIDs'] = lst[1:]
		if not stop_loop:	unresolved = newUnresolved
	except IndexError:
		if not stop_loop:	unresolved = None






@app.route('/')
def main():
	if 'X-Replit-User-Name' in flask.request.headers:
		if flask.request.headers['X-Replit-User-Name'] != '':
			if 'moderator' in flask.request.headers['X-Replit-User-Roles'].split(','):
				if unresolved != None:
					return flask.render_template('mod.html', unresolved=unresolved, plural=lambda a: plural(a))
				return flask.render_template('no_reports.html')
			return 'no'
	return flask.render_template('index.html')


@app.route('/resolve', methods=['POST'])
def resolve_route():
	if 'moderator' in flask.request.headers['X-Replit-User-Roles'].split(','):
		resolve = flask.request.args.get('ids').split(',')
		global unresolved, stop_loop
		posts = []
		postsAndReports = []
		for post in unresolved:
			if resolve == unresolved[post]['reportIDs'].split(','):
				for i in unresolved[post]['reporters']:
					asyncio.run(unresolved[post]['reporters'][i]['report'].resolve())
				posts.append(post)
				stop_loop = True
			else:
				if post != 'deleted':
					for report in unresolved[post]['reporters']:
						if str(unresolved[post]['reporters'][report]['reportID']) in resolve:
							asyncio.run(unresolved[post]['reporters'][report]['report'].resolve())
							postsAndReports.append([post, report])
							stop_loop = True
				else:
					for i in unresolved[post]['reporters']:
						print(resolve)
						print(i)
						if i in resolve:
							asyncio.run(unresolved[post]['reporters'][i]['report'].resolve())
							postsAndReports.append([post, i])
							stop_loop = True
		for post in posts:
			del unresolved[post]
		for lst in postsAndReports:
			if lst[0] != 'deleted':
				del unresolved[lst[0]]['reporters'][lst[1]]
			else:
				del unresolved[lst[0]]['reporters'][lst[1]]

		if unresolved == {}:
			unresolved = None
		return flask.redirect('https://reports.codingcactus.repl.co')

	return 'no'

@app.route('/favicon.ico')
def favicon():
	return flask.send_file('./static/favicon.ico')
	

asyncio.run(refresh_reports())
refresh(60)
app.run('0.0.0.0')