import React from 'react';

interface UserAvatarProps {
  username: string;
}

const UserAvatar: React.FC<UserAvatarProps> = ({ username }) => {
  return (
    <div style={{
      width: 32,
      height: 32,
      borderRadius: '50%',
      background: '#1677ff',
      color: '#fff',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontWeight: 600,
      fontSize: 16,
    }}>
      {username.slice(0, 1).toUpperCase()}
    </div>
  );
};

export default UserAvatar;
