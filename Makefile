rsync-pibell-0: 
	@echo "*** rsyncing to pibell-0"
	@rsync -r . pi@pibell-0.lan:/home/pi/source/home-dash

update-pibell-0: rsync-pibell-0
	@echo "*** updating dash-api docker image"
	@ssh pi@pibell-0.lan "cd source/home-dash/dash-api && docker build -t pibell-0.lan:5000/dash-api . && docker push pibell-0.lan:5000/dash-api"
	@echo "*** updating leaf-status docker image"
	@ssh pi@pibell-0.lan "cd source/home-dash/leaf-status && docker build -t pibell-0.lan:5000/leaf-status . && docker push pibell-0.lan:5000/leaf-status"
	@echo "*** applying k8s manifests"
	@kubectl apply -f deploy