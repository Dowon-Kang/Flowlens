import axios from 'axios';
export async function listTasks() {
  return axios.get('/api/tasks');
}
export async function addTask() {
  return axios.post('/api/tasks', {title: 'demo'});
}
