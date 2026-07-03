import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { BrowserRouter } from 'react-router-dom';
import ChildProfile from '../pages/ChildProfile';
import { useAuth } from '../contexts/AuthContext';

// Mock dependencies
vi.mock('axios');

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}));

const mockChildData = {
  id: 1,
  name: 'Test Child',
  child_code: 'TC001',
  legal_status: 'pending_inquiry',
  estimated_age: 10,
  gender: 'Male',
  admission_category: 'abandoned',
  admission_date: '2023-01-01',
  cci_name: 'Test CCI',
  case_history: []
};

describe('ChildProfile Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ token: 'test-token' });
  });

  it('renders loading state initially', () => {
    // Return unresolved promises to keep it in loading state
    axios.get.mockReturnValue(new Promise(() => {}));
    
    render(
      <BrowserRouter>
        <ChildProfile id={1} />
      </BrowserRouter>
    );

    expect(screen.getByText('Loading case file...')).toBeInTheDocument();
  });

  it('renders "Schedule hearing" when no active hearing is present', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/visits')) return Promise.resolve({ data: [] });
      if (url.includes('/hearings')) return Promise.resolve({ data: [] });
      return Promise.resolve({ data: { data: mockChildData } });
    });

    render(
      <BrowserRouter>
        <ChildProfile id={1} />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Child')).toBeInTheDocument();
    });

    expect(screen.getByText('Schedule hearing')).toBeInTheDocument();
  });

  it('renders "Go to hearing" button when active hearing is present and shows overlay on click', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/visits')) return Promise.resolve({ data: [] });
      if (url.includes('/hearings')) return Promise.resolve({ data: [{ child_id: 1, status: 'scheduled' }] });
      return Promise.resolve({ data: { data: mockChildData } });
    });

    render(
      <BrowserRouter>
        <ChildProfile id={1} />
      </BrowserRouter>
    );

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('Test Child')).toBeInTheDocument();
    });

    const hearingButton = screen.getByText('Go to hearing');
    expect(hearingButton).toBeInTheDocument();

    // Click the button
    fireEvent.click(hearingButton);

    // Expect the overlay to appear
    expect(screen.getByText('Preparing hearing console...')).toBeInTheDocument();

    // Expect navigation to occur after 500ms
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/hearings?child_id=1');
    }, { timeout: 1000 });
  });

  it('shows error state on API failure', async () => {
    axios.get.mockRejectedValue(new Error('Network error'));
    
    render(
      <BrowserRouter>
        <ChildProfile id={1} />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Failed to load child details. Please try again.')).toBeInTheDocument();
    });
  });
});
