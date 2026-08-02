import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '10s',
  thresholds: {
    'http_req_duration': ['p(95)<150'],
  },
};

const BASE_URL = 'http://localhost:8000';

export function setup() {
  // Trigger audit store outage prior to running load test
  const res = http.post(`${BASE_URL}/system/simulate-outage`, null, {
    headers: {
      'X-User-Id': 'admin_k6',
      'X-User-Role': 'admin',
    },
  });
  check(res, { 'outage simulated successfully': (r) => r.status === 200 });
}

export default function () {
  // Doctor Read (FAIL-OPEN expected)
  const docRes = http.get(`${BASE_URL}/patients/P100`, {
    headers: {
      'X-User-Id': 'doc_k6',
      'X-User-Role': 'doctor',
    },
  });
  check(docRes, {
    'doctor read succeeds under outage (200)': (r) => r.status === 200,
    'degraded header present for doctor': (r) => r.headers['X-System-Degraded'] === 'true',
  });

  // Billing Read (FAIL-CLOSED expected)
  const billRes = http.get(`${BASE_URL}/patients/P100`, {
    headers: {
      'X-User-Id': 'bill_k6',
      'X-User-Role': 'billing',
    },
  });
  check(billRes, {
    'billing read blocked under outage (503)': (r) => r.status === 503,
  });

  sleep(0.1);
}

export function teardown() {
  // Recover system post-test
  http.post(`${BASE_URL}/system/recover`, null, {
    headers: {
      'X-User-Id': 'admin_k6',
      'X-User-Role': 'admin',
    },
  });
}
