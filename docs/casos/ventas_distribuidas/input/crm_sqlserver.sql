-- CRM comercial (SQL Server). Script generado con "Generate Scripts > Schema only".

CREATE TABLE [dbo].[Accounts] (
    [AccountId] INT NOT NULL PRIMARY KEY,
    [Name] NVARCHAR(200) NOT NULL,
    [TaxId] VARCHAR(20) NULL,
    [Segment] NVARCHAR(50) NULL,
    [ErpCustomerCode] VARCHAR(20) NULL,
    [OwnerEmail] NVARCHAR(200) NULL
);

CREATE TABLE [dbo].[Opportunities] (
    [OpportunityId] INT NOT NULL PRIMARY KEY,
    [AccountId] INT NOT NULL REFERENCES [dbo].[Accounts]([AccountId]),
    [Stage] NVARCHAR(30) NOT NULL,
    [Amount] DECIMAL(14,2) NULL,
    [CloseDate] DATE NULL,
    [CheckinDate] DATE NULL
);

CREATE TABLE [dbo].[Contacts] (
    [ContactId] INT NOT NULL,
    [AccountId] INT NOT NULL,
    [FullName] NVARCHAR(200) NULL,
    [Email] NVARCHAR(200) NULL,
    CONSTRAINT [PK_Contacts] PRIMARY KEY ([ContactId]),
    CONSTRAINT [FK_Contacts_Accounts] FOREIGN KEY ([AccountId]) REFERENCES [dbo].[Accounts]([AccountId])
);
