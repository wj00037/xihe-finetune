MAINTAINER zengchen1024<chenzeng765@gmail.com>

# build binary
COPY . /go/src/github.com/opensourceways/xihe-finetune
RUN cd /go/src/github.com/opensourceways/xihe-finetune && GO111MODULE=on CGO_ENABLED=0 go build -o xihe-finetune

# copy binary config and utils
FROM alpine:3.14
RUN apk update && apk add --no-cache \
        git \
        bash \
        libc6-compat

RUN adduser mindspore -u 5000 -D
USER mindspore
WORKDIR /opt/app

COPY --from=BUILDER /go/src/github.com/opensourceways/xihe-finetune/xihe-finetune /opt/app

ENTRYPOINT ["/opt/app/xihe-finetune"]

