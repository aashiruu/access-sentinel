import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '5s', target: 10 },
    { duration: '10s', target: 20 },
    { duration: '5s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<100'], // 95% of requests must complete within 100ms
    http_req_failed: ['rate<0.01'],    // Error rate under 1%
  },
};

const BASE_URL = 'http://localhost:8000';

export default function () {
  // Doctor Read
  const docRes = http.get(`${BASE_URL}/patients/P100`, {
    headers: {
      'X-User-Id': 'doc_k6',
      'X-User-Role': 'doctor',
    },
  });
  check(docRes, {
    'doctor access status is 200': (r) => r.status === 200,
    'doctor sees clinical and billing': (r) => {
      const body = JSON.parse(r.body);
      return body.clinical !== null && body.billing !== null;
    },
  });

  // Nurse Read
  const nurseRes = http.get(`${BASE_URL}/patients/P100`, {
    headers: {
      'X-User-Id': 'nurse_k6',
      'X-User-Role': 'nurse',
    },
  });
  check(nurseRes, {
    'nurse access status is 200': (r) => r.status === 200,
    'nurse sees clinical but no billing': (r) => {
      const body = JSON.parse(r.body);
      return body.clinical !== null && body.billing === null;
    },
  });

  sleep(0.1);
}
