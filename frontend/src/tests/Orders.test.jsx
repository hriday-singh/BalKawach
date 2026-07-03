import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import Orders from '../pages/Orders';
import { useAuth } from '../contexts/AuthContext';

// Mock dependencies
vi.mock('axios');

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}));

const mockOrdersData = [
  {
    id: 1,
    order_number: 'ORD-2023-001',
    status: 'pending_approval',
    order_type: 'interim_custody',
    created_at: '2023-05-10T10:00:00Z',
    child_id: 101,
    child: { name: 'Alice Smith' },
    content: 'Order content here'
  },
  {
    id: 2,
    order_number: 'ORD-2023-002',
    status: 'approved',
    order_type: 'final_disposition',
    created_at: '2023-05-12T11:00:00Z',
    child_id: 102,
    // Note: missing child object to test fallback to child_id
  }
];

describe('Orders Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ token: 'test-token', user: { role: 'cwc_chairperson' } });
  });

  it('renders loading state initially', () => {
    axios.get.mockReturnValue(new Promise(() => {}));
    
    render(<Orders />);
    expect(screen.getByText('Loading orders...')).toBeInTheDocument();
  });

  it('renders orders with child names correctly', async () => {
    axios.get.mockResolvedValue({ data: { data: mockOrdersData } });

    render(<Orders />);

    await waitFor(() => {
      expect(screen.queryByText('Loading orders...')).not.toBeInTheDocument();
    });

    // Verify order numbers
    expect(screen.getByText('ORD-2023-001')).toBeInTheDocument();
    expect(screen.getByText('ORD-2023-002')).toBeInTheDocument();

    // Verify child name fallback
    expect(screen.getByText('Alice Smith')).toBeInTheDocument();
    expect(screen.getByText('102')).toBeInTheDocument(); // fallback when child.name is missing

    // Verify status badges
    expect(screen.getByText('PENDING APPROVAL')).toBeInTheDocument();
    expect(screen.getByText('APPROVED')).toBeInTheDocument();
  });

  it('shows empty state when no orders exist', async () => {
    axios.get.mockResolvedValue({ data: [] });

    render(<Orders />);

    await waitFor(() => {
      expect(screen.getByText('No orders found')).toBeInTheDocument();
    });
  });

  it('opens modal with order details and allows approval if chairperson', async () => {
    axios.get.mockResolvedValue({ data: mockOrdersData });
    axios.put.mockResolvedValue({ data: { success: true } });

    render(<Orders />);

    await waitFor(() => {
      expect(screen.getByText('ORD-2023-001')).toBeInTheDocument();
    });

    // Find and click View Details for the first order
    const viewDetailsButtons = screen.getAllByText('View Details');
    fireEvent.click(viewDetailsButtons[0]);

    // Check if modal opens
    expect(screen.getByText('Order Details: ORD-2023-001')).toBeInTheDocument();
    expect(screen.getByText('Order Content / Directives:')).toBeInTheDocument();
    expect(screen.getByText('Order content here')).toBeInTheDocument();

    // Click Approve in the modal
    const approveButton = screen.getAllByText('Approve')[1]; // One might be outside the modal (depends on UI structure), wait, the one in modal has the icon too.
    // Let's grab the one inside the modal. In the component, "Approve" text is rendered in both the card and the modal.
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledWith('/api/orders/1/approve', {}, expect.any(Object));
    });
  });

  it('handles error state', async () => {
    axios.get.mockRejectedValue(new Error('Failed to load'));

    render(<Orders />);

    await waitFor(() => {
      expect(screen.getByText(/Error: Failed to load/)).toBeInTheDocument();
    });
  });
});
