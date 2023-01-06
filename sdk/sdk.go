package sdk

import (
	"bytes"
	"fmt"
	"net/http"
	"strings"

	"github.com/opensourceways/community-robot-lib/utils"

	"github.com/opensourceways/xihe-finetune/app"
	"github.com/opensourceways/xihe-finetune/controller"
)

type LogURL = app.LogURLDTO
type JobInfo = app.JobInfoDTO
type FinetuneCreateOption = controller.FinetuneCreateRequest

func New(endpoint string) Finetune {
	s := strings.TrimSuffix(endpoint, "/")
	if p := "/api/v1/finetune"; !strings.HasSuffix(s, p) {
		s += p
	}

	return Finetune{
		endpoint: s,
		cli:      utils.NewHttpClient(3),
	}
}

type Finetune struct {
	endpoint string
	cli      utils.HttpClient
}

func (t Finetune) jobURL(jobId string) string {
	return fmt.Sprintf("%s/%s", t.endpoint, jobId)
}

func (t Finetune) Create(opt *FinetuneCreateOption) (
	dto JobInfo, err error,
) {
	payload, err := utils.JsonMarshal(&opt)
	if err != nil {
		return
	}

	req, err := http.NewRequest(http.MethodPost, t.endpoint, bytes.NewBuffer(payload))
	if err != nil {
		return
	}

	v := new(app.JobInfoDTO)
	if err = t.forwardTo(req, v); err != nil {
		return
	}

	return *v, nil
}

func (t Finetune) Delete(jobId string) error {
	req, err := http.NewRequest(http.MethodDelete, t.jobURL(jobId), nil)
	if err != nil {
		return err
	}

	return t.forwardTo(req, nil)
}

func (t Finetune) Terminate(jobId string) error {
	req, err := http.NewRequest(http.MethodPut, t.jobURL(jobId), nil)
	if err != nil {
		return err
	}

	return t.forwardTo(req, nil)
}

func (t Finetune) GetLogDownloadURL(jobId string) (r LogURL, err error) {
	req, err := http.NewRequest(http.MethodGet, t.jobURL(jobId)+"/log", nil)
	if err != nil {
		return
	}

	err = t.forwardTo(req, &r)

	return
}

func (t Finetune) forwardTo(req *http.Request, jsonResp interface{}) (err error) {
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "xihe-finetune")

	if jsonResp != nil {
		v := struct {
			Data interface{} `json:"data"`
		}{jsonResp}

		_, err = t.cli.ForwardTo(req, &v)
	} else {
		_, err = t.cli.ForwardTo(req, jsonResp)
	}

	return
}
