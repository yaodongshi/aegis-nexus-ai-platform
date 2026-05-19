import React from 'react';
import { useNavigate } from 'react-router-dom';

import ProviderWizard from './wizard';

export default function ProviderCreatePage() {
  const navigate = useNavigate();

  return (
    <div>
      <ProviderWizard
        embedded={false}
        onCancel={() => navigate('/providers')}
        onDone={(providerId) => navigate(`/providers/${providerId}`)}
      />
    </div>
  );
}