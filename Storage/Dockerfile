# This Dockerfile builds the server part only.
# EXPOSE NEED PORT FROM config.yaml

FROM python:3.12
WORKDIR /serverFiles
COPY . .
RUN pip install -r ./requirements.txt

EXPOSE 12345/tcp
ENTRYPOINT [ "python" ]
CMD ["./storage.py"]
