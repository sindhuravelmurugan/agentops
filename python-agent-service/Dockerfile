FROM golang:1.22-alpine AS build

WORKDIR /app
COPY go.mod ./
COPY . .
RUN go mod tidy && go build -o gateway .

FROM alpine:3.20
COPY --from=build /app/gateway /gateway
EXPOSE 8080
CMD ["/gateway"]