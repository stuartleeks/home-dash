# syntax=docker/dockerfile:1

FROM golang:1.23 AS build-stage

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o /dash-api

# Run the tests in the container
# FROM build-stage AS run-test-stage
# RUN go test -v ./...

FROM gcr.io/distroless/base-debian11 AS build-release-stage

WORKDIR /

COPY --from=build-stage /app/fonts /fonts
COPY --from=build-stage /app/leaf_images /leaf_images
COPY --from=build-stage /dash-api /dash-api

EXPOSE 8080

# USER nonroot:nonroot

ENTRYPOINT ["/dash-api"]