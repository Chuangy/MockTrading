module.exports = {
	apps : [{
		name	: "python-backend",
		script	: "manage.py",
		interpreter : "./venv/bin/python",
		watch	: true,
	},
	{
		name	: "react-frontend",
		script	: "serve",
		watch	: true,
		env	: {
			PM2_SERVE_PATH: './frontend/build/',
			PM2_SERVE_PORT: 8080,
		}
	}]
}
