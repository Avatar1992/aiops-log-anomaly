FROM python:3.10-slim
WORKDIR /app
COPY generator.py /app/generator.py
RUN mkdir -p /var/log/app
VOLUME ["/var/log/app"]
CMD ["python", "generator.py"]

