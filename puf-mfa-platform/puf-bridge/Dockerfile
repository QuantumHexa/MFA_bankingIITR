FROM python:3.12-slim
WORKDIR /app
COPY virtual_puf_server.py .
EXPOSE 8765
CMD ["python", "virtual_puf_server.py", "--host", "0.0.0.0", "--port", "8765"]
