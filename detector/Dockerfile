FROM python:3.10-slim
WORKDIR /detector
COPY requirements.txt /detector/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY detector.py /detector/detector.py
CMD ["python", "detector.py"]

