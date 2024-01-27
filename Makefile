rsync-pibell-0: 
	rsync -r . pi@pibell-0:/home/pi/source/home-dash

run:
	uvicorn main:app --reload