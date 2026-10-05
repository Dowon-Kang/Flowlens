import React from 'react';
import { listTasks } from './task_service';
export function TaskView() {
  return <button onClick={listTasks}>Load tasks</button>;
}
