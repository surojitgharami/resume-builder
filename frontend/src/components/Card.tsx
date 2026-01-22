import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'glass' | 'gradient';
  hover?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  variant = 'default',
  hover = true,
}) => {
  const variants = {
    default: 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700',
    glass: 'glass',
    gradient: 'bg-gradient-to-br from-primary-50 to-secondary-50 dark:from-gray-800 dark:to-gray-900 border border-primary-200 dark:border-gray-700',
  };
  
  const hoverClass = hover ? 'hover:shadow-xl transform hover:-translate-y-1' : '';
  
  return (
    <div className={`rounded-xl shadow-lg transition-all duration-300 ${variants[variant]} ${hoverClass} ${className}`}>
      {children}
    </div>
  );
};
