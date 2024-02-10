# This Dockerfile builds the web part only.

FROM python:3.12
WORKDIR /webFiles
COPY . .
RUN pip install -r ./requirements.txt

EXPOSE 5000
ENTRYPOINT [ "python" ]
CMD ["./app.py"]
