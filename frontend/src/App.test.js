// Author: Yuan Tian
// Gtihub: https://github.com/magic-YuanTian/SQLsynth

import { render, screen } from '@testing-library/react';
import App from './App';

test('renders learn react link', () => {
  render(<App />);
  const linkElement = screen.getByText(/learn react/i);
  expect(linkElement).toBeInTheDocument();
});
