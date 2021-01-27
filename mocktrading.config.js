module.exports = {
	apps : [{
		name	: "python-backend",
		script	: "manage.py",
		interpreter : "./venv/bin/python",
		watch	: true,
		env		: {
			"PRIVATE_HOST" : "localhost",
			"PUBLIC_HOST" : "localhost",
			"PORT" : 8887
		},
		env_production: {
			"PRIVATE_HOST" : "172.31.19.134",
			"PUBLIC_HOST" : "54.252.192.246",
			"PORT" : 8887
		},
	},
	{
		name	: "react-frontend",
		script	: "serve",
		watch	: true,
		env	: {
			"PM2_SERVE_PATH": './frontend/build/',
			"PM2_SERVE_PORT": 3000,
		},
		env_production: {
			"PM2_SERVE_PATH": './frontend/build/',
			"PM2_SERVE_PORT": 8080,
		},
	}]
}