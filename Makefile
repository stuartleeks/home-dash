rsync-pibell-0: 
	@echo "*** rsyncing to pibell-0"
	@rsync -r . pi@pibell-0.lan:/home/pi/source/home-dash

update-pibell-0:
	@echo "*** updating dash-api docker image"
	@cd dash-api && docker build -t localhost:5000/dash-api .
	@echo "*** updating leaf-status docker image"
	@cd leaf-status && docker build -t localhost:5000/leaf-status .
	@echo "*** applying k8s manifests"
	@kubectl apply -f deploy
	@kubectl delete pod --selector app=dash-api # restart pod to apply changes