# rsync-pibell-0: 
# 	rsync -r . pi@pibell-0.lan:/home/pi/source/home-dash

# update-pibell-0: rsync-pibell-0
# 	 ssh pi@pibell-0.lan "cd source/home-dash/ &&  docker build -t home-dash . && sudo systemctl restart home-dash.service && docker image prune -f && curl http://localhost:8000"

run:
	uvicorn main:app --reload