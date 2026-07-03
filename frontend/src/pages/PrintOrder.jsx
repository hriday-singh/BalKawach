import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export default function PrintOrder() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchOrder = async () => {
      try {
        const res = await axios.get(`/api/orders/${id}/print`);
        setOrder(res.data);
        // Do not print here, handle it in a separate effect
      } catch (err) {
        setError('Failed to load order for printing');
      } finally {
        setLoading(false);
      }
    };
    fetchOrder();
  }, [id]);

  const hasPrinted = React.useRef(false);
  useEffect(() => {
    const handleAfterPrint = () => window.close();
    window.addEventListener('afterprint', handleAfterPrint);

    if (!loading && order && !hasPrinted.current) {
      hasPrinted.current = true;
      setTimeout(() => {
        window.print();
      }, 500);
    }

    return () => window.removeEventListener('afterprint', handleAfterPrint);
  }, [loading, order]);

  if (loading) return (
    <div style={{ padding: '60px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', color: 'var(--muted)' }}>
      <Loader2 size={32} style={{ animation: 'spin 1s linear infinite' }} />
      <p>Preparing document...</p>
    </div>
  );

  if (error || !order) return <div style={{ padding: '2rem', color: 'red' }}>{error || 'Order not found'}</div>;

  return (
    <div className="print-order" style={{ 
      background: 'white', 
      color: 'black', 
      minHeight: '100vh',
      padding: '2rem',
      fontFamily: '"Times New Roman", Times, serif'
    }}>
      <div className="print-header">
        <h1>Child Welfare Committee</h1>
        <h2>District {order.district || '___________'}, Government of {order.state || 'India'}</h2>
      </div>

      <table className="print-meta" style={{ width: '100%', marginBottom: '24px' }}>
        <tbody>
          <tr>
            <td><strong>Order Number:</strong> {order.order_number}</td>
            <td><strong>Child Name:</strong> {order.child?.name || order.child_id}</td>
          </tr>
          <tr>
            <td><strong>Date:</strong> {new Date(order.created_at).toLocaleDateString()}</td>
            <td><strong>Child Case No:</strong> {order.child?.child_code || 'N/A'}</td>
          </tr>
          <tr>
            <td><strong>Order Type:</strong> {order.order_type ? order.order_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'N/A'}</td>
            <td><strong>Status:</strong> {order.status.replace(/_/g, ' ').toUpperCase()}</td>
          </tr>
        </tbody>
      </table>

      <div className="order-body">
        <h3 style={{ textTransform: 'uppercase', fontSize: '12pt', marginBottom: '8px' }}>Findings & Observations</h3>
        <div style={{ whiteSpace: 'pre-wrap', marginBottom: '24px' }}>
          {order.findings || "No specific findings recorded."}
        </div>

        <h3 style={{ textTransform: 'uppercase', fontSize: '12pt', marginBottom: '8px' }}>Order & Directives</h3>
        <div style={{ whiteSpace: 'pre-wrap' }}>
          {order.order_body || "No directives provided."}
        </div>
      </div>

      <div className="signatures">
        <div className="sig-block">
          <div className="sig-line"></div>
          <strong>Member, CWC</strong>
          <div style={{ fontSize: '11pt', marginTop: '4px' }}>{order.created_by}</div>
        </div>
        <div className="sig-block">
          <div className="sig-line"></div>
          <strong>Chairperson, CWC</strong>
          <div style={{ fontSize: '11pt', marginTop: '4px' }}>{order.approved_by || '__________________'}</div>
        </div>
      </div>

      <div style={{ marginTop: '4rem', textAlign: 'center', fontSize: '12px', color: '#666' }} className="print-footer">
        Generated electronically via BalKawach platform on {new Date(order.generated_at || Date.now()).toLocaleString()}
      </div>


    </div>
  );
}
