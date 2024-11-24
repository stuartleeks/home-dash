rsync-pibell-0: 
	@echo "*** rsyncing to pibell-0"
	@rsync -r . pi@pibell-0.lan:/home/pi/source/home-dash

update-pibell-0: rsync-pibell-0
	@echo "*** updating dash-api docker image"
	@#cd dash-api && docker build --platform linux/arm -t pibell-0.lan:5000/dash-api . && docker push pibell-0.lan:5000/dash-api:latest
	@ssh pi@pibell-0.lan "cd source/home-dash/dash-api && docker build -t pibell-0.lan:5000/dash-api . && docker push pibell-0.lan:5000/dash-api:latest"

	@echo "*** updating leaf-status docker image"
	@#cd leaf-status && docker build -t pibell-0.lan:5000/leaf-status . && docker push pibell-0.lan:5000/leaf-status:latest
	@ssh pi@pibell-0.lan "cd source/home-dash/leaf-status && docker build -t pibell-0.lan:5000/leaf-status . && docker push pibell-0.lan:5000/leaf-status:latest"

	@echo "*** updating fetch-stocks docker image"
	@#cd fetch-stocks && docker build -t pibell-0.lan:5000/fetch-stocks . && docker push pibell-0.lan:5000/fetch-stocks:latest
	@ssh pi@pibell-0.lan "cd source/home-dash/fetch-stocks && docker build -t pibell-0.lan:5000/fetch-stocks . && docker push pibell-0.lan:5000/fetch-stocks:latest"

	@echo "*** updating fetch-weather docker image"
	@#cd fetch-weather && docker build -t pibell-0.lan:5000/fetch-weather . && docker push pibell-0.lan:5000/fetch-weather:latest
	@ssh pi@pibell-0.lan "cd source/home-dash/fetch-weather && docker build -t pibell-0.lan:5000/fetch-weather . && docker push pibell-0.lan:5000/fetch-weather:latest"
	
	@echo "*** applying k8s manifests"
	@kubectl apply -f deploy
	@kubectl delete pod --selector app=dash-api # restart pod to apply changes


rsync-temp-sensor: 
	@echo "*** rsyncing to pistat-0"
	@rsync -r . pi@pistat-0.lan:/home/pi/source/home-dash
